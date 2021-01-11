# -*- coding utf-8 -*-#
# ------------------------------------------------------------------
# Name:      db_test
# Author:    liangbaikai
# Date:      2021/1/8
# Desc:      there is a python file description
# ------------------------------------------------------------------

import asyncio

from spiders.db.sanicdb import SanicDB


async def test(loop):
    db = SanicDB('localhost', 'testdb', 'root', 'root',
                 minsize=3, maxsize=5,
                 connect_timeout=5,
                 loop=None)
    sql = 'Drop table test'
    await db.execute(sql)

    sql = """CREATE TABLE `test` (
    `id` int(8) NOT NULL AUTO_INCREMENT,
    `name` varchar(16) NOT NULL,
    `content` varchar(255) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `name` (`name`)
    ) ENGINE=MyISAM ;"""
    await db.execute(sql)

    sql = 'select * from test where name = %s'
    data = await db.query(sql, 'abc')
    print('query():', data)

    sql += ' limit 1'
    d = await db.get(sql, 'abc')
    print('get():', d)

    sql = 'delete from test where name=%s'
    lastrowid = await db.execute(sql, 'xyz')
    print('execute(delete...):', lastrowid)
    sql = 'insert into test set name=%s, content=%s'
    lastrowid = await db.execute(sql, 'xyz', '456')
    print('execute(insert...):', lastrowid)

    ret = await db.table_has('test', 'name', 'abc')
    print('has(): ', ret)

    ret = await db.table_update('test', {'content': 'updated'},
                                'name', 'abc')
    print('update():', ret)
    sql = 'select * from test where name = %s'
    data = await db.query(sql, 'abc')
    print('query():', data)

    item = {
        'name': 'abc',
        'content': '123'
    }
    i = 0
    while 1:
        i += 1
        if i % 2 == 0:
            lastid = await db.table_insert('test', item, ignore_duplicated=True)
        else:
            lastid = await db.table_insert('test', item)
        item.update(name=i)
        print('insert():', lastid)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
