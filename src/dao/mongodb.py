# -*- coding: utf-8 -*-

from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

from submodules.utils.singleton import SingletonMetaThreadSafe as SingletonMetaclass
from submodules.utils.sys_env import SysEnv
from submodules.utils.logger import Logger
from submodules.utils.profile import FuncTimeExpend

logger = Logger()


class MongoDBReplicaHelper(metaclass=SingletonMetaclass):

    def __init__(self):
        super().__init__()
        host = SysEnv.get("MONGODB_CLUSTER_NODES")
        auth_db = SysEnv.get("MONGODB_CLUSTER_AUTH_DB")
        username = SysEnv.get("MONGODB_CLUSTER_USER")
        password = SysEnv.get("MONGODB_CLUSTER_PASSWORD")
        replica_set = SysEnv.get("MONGODB_CLUSTER_REPLICA_SET")
        min_pool_size = int(SysEnv.get("R_MONGODB_MIN_POOL_SIZE", 512))
        max_pool_size = int(SysEnv.get("R_MONGODB_MAX_POOL_SIZE", 8192))
        replica_set_number = int(SysEnv.get("R_MONGODB_REPLICA_SET_NUMBER", 3))
        connection_string = f"mongodb://{username}:{password}@{host}/{auth_db}?replicaSet={replica_set}"
        logger.info(connection_string)
        self.mongo_client = MongoClient(
            connection_string,
            minPoolSize=min_pool_size, maxPoolSize=max_pool_size,
            w=replica_set_number, readPreference="secondaryPreferred")
        coll = self.coll.split("___")
        self._coll = self.mongo_client[coll[1]][coll[2]]


class MongoDBSingleHelper(metaclass=SingletonMetaclass):

    def __init__(self):
        super().__init__()
        host = SysEnv.get("MONGODB_SERVER_ADDRESS")
        port = int(SysEnv.get("MONGODB_PORT"))
        username = SysEnv.get("MONGODB_USER_NAME")
        password = SysEnv.get("MONGODB_USER_PASSWORD")
        self.mongo_client = MongoClient(
            host=host,
            port=port,
            username=username,
            password=password
        )
        coll = self.coll.split("___")
        self._coll = self.mongo_client[coll[1]][coll[2]]


if SysEnv.get("R_ENABLE_REPLICA"):
    class MongoDBHelper(MongoDBReplicaHelper):
        pass
else:
    class MongoDBHelper(MongoDBSingleHelper):
        pass

async def insert_one(self, json_obj):
    return await self._coll.insert_one(json_obj)

async def update_one(self, matcher, json_obj, upsert=False):
    return await self._coll.update_one(matcher, {"$set": json_obj}, upsert=upsert)


async def find_one(self, matcher, exclude=None):
    if exclude is not None:
        obj = await self._coll.find_one(matcher, exclude)
    else:
        obj = await self._coll.find_one(matcher)
    return obj


def count(self, matcher):
    count = self._coll.count_documents(matcher)
    return count


async def delete_one(self, matcher):
    return await self._coll.delete_one(matcher)


@FuncTimeExpend(prefix="Find Many: ")
async def find_many(self, matcher, sortby=None, page=None, size=None):
    # 默认为按照更新时间倒序
    if sortby is None:
        sortby = [("updateTime", -1)]
    if page is None:
        page = 1
    if size is None:
        size = 100
    page = int(page)
    size = int(size)
    skip = (page - 1) * size
    logger.info(f"Find Many: {matcher} -> sortby: {sortby}, skip: {skip} size: {size}")
    async for result in self._coll.find(matcher).sort(sortby).skip(skip).limit(size):
        yield result


def pkg_matcher(self, matcher):
    result = {}
    if matcher is not None:
        for m in matcher:
            v = m.v
            k = m.k
            t = m.t or self.C.EXACT_MATCH
            if None in (k, t, v):
                continue
            if t == self.C.EXACT_MATCH:
                pass
            elif t == self.C.PREFIX_MATCH:
                v = {"$regex": f".*{v}$"}
            elif t == self.C.SUFFIX_MATCH:
                v = {"$regex": f"^{v}.*"}
            else:
                v = {"$regex": f".*{v}.*"}
            result.update({k: v})
    logger.info(f">>>>> pkg_matcher <<<<<<: {result}")
    return result


setattr(MongoDBHelper, "insert_one", insert_one)
setattr(MongoDBHelper, "update_one", update_one)
setattr(MongoDBHelper, "find_one", find_one)
setattr(MongoDBHelper, "count", count)
setattr(MongoDBHelper, "delete_one", delete_one)
setattr(MongoDBHelper, "find_many", find_many)
setattr(MongoDBHelper, "pkg_matcher", pkg_matcher)
