#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections

READ_COMMANDS = frozenset([
    'BITCOUNT',
    'BITPOS',
    'DBSIZE',
    'ECHO',
    'EXISTS',
    'GET',
    'GETBIT',
    'GETRANGE',
    'HEXISTS',
    'HGET',
    'HGETALL',
    'HKEYS',
    'HLEN',
    'HMGET',
    'HSCAN',
    'HVALS',
    'INFO',
    'KEYS',
    'LINDEX',
    'LLEN',
    'LRANGE',
    'MGET',
    'PING',
    'PTTL',
    'RANDOMKEY',
    'SCAN',
    'SCARD',
    'SDIFF',
    'SINTER',
    'SISMEMBER',
    'SMEMBERS',
    'SRANDMEMBER',
    'SSCAN',
    'STRLEN',
    'SUNION',
    'TIME',
    'TTL',
    'TYPE',
    'ZCARD',
    'ZCOUNT',
    'ZLEXCOUNT',
    'ZRANGE',
    'ZRANGEBYLEX',
    'ZRANGEBYSCORE',
    'ZRANK',
    'ZREVRANGE',
    'ZREVRANGEBYSCORE',
    'ZREVRANK',
    'ZSCAN',
    'ZSCORE',
])

WRITE_COMMANDS = frozenset([
    'APPEND',
    'BITOP',
    'BLPOP',
    'BRPOP',
    'BRPOPLPUSH',
    'DECR',
    'DECRBY',
    'DEL',
    'EXPIRE',
    'EXPIREAT',
    'FLUSHALL',
    'FLUSHDB',
    'GETSET',
    'HDEL',
    'HINCRBY',
    'HINCRBYFLOAT',
    'HMSET',
    'HSET',
    'HSETNX',
    'INCR',
    'INCRBY',
    'INCRBYFLOAT',
    'LINSERT',
    'LPOP',
    'LPUSH',
    'LPUSHX',
    'LREM',
    'LSET',
    'LTRIM',
    'MOVE',
    'MSET',
    'MSETNX',
    'PEXPIRE',
    'PEXPIREAT',
    'PFADD',
    'PFCOUNT',
    'RPOP',
    'RPOPLPUSH',
    'RPUSH',
    'RPUSHX',
    'SADD',
    'SET',
    'SETBIT',
    'SETEX',
    'SETNX',
    'SETRANGE',
    'SMOVE',
    'SORT',
    'SPOP',
    'SREM',
    'ZADD',
    'ZINCRBY',
    'ZREM',
    'ZREMRANGEBYLEX',
    'ZREMRANGEBYRANK',
    'ZREMRANGEBYSCORE',
])


class Connection(collections.namedtuple('Connection', 'host port db')):

    @classmethod
    def create(cls, **kwargs):
        kwargs.setdefault('port', 6379)
        kwargs.setdefault('db', 0)
        return cls(**kwargs)

    @classmethod
    def from_str(cls, s):
        parts = s.split(':')
        host, parts = parts
        port, db = parts.split('/')
        port = int(port)
        db = int(db)
        return cls.create(host=host, port=port, db=db)

    def __str__(self):
        return '{host}:{port}/{db}'.format(**self._asdict())

    def group_name_prefix(self):
        return str(self).replace(':', '-')

    @classmethod
    def from_group_name(cls, s):
        '''
        >>> Connection.from_group_name('myhost123-6380/1-reader')
        Connection(host='myhost123', port=6380, db=1)
        '''

        return cls.from_str(':'.join(s.rsplit('-', 2)[:-1]))


