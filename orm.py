import asyncio, aiomysql, logging

def log(sql, args = ()):
	'记录SQL操作'
	logging.info('SQL: %s' %sql)

async def create_pool(loop, **kw):
	'创建全局连接池，**kw 关键字参数集，用于传递host port user password db等的数据库连接参数.'
	logging.info('create database connection pool...')
	global __pool
	__pool = await aiomysql.create_pool(
			host = kw.get('host', 'localhost'),#get(关键字参数，默认值)设置主机为本机
			port = kw.get('port', 3306),#设置端口为3306
			user = kw['user'],#数据库账户
			password = kw['password'],#账户密码
			db = kw['db'],#选择数据库
			charset = kw.get('charset', 'utf8'),#设置数据库编码，默认为utf8
			autocommit = kw.get('autocommit', True),#设置自动提交事务，默认开启
			maxsize = kw.get('maxsize', 10),#设置最大连接数为10
			minsize = kw.get('minsize', 1),#设置最少连接数为1
			loop = loop #传递循环实例，默认使用asyncio.get_event_loop()
			)

async def destroy_pool():
	global __pool
	if __pool is not None:
		__pool.close()
		await __pool.wait_closed()
		
async def select(sql, args, size = None):
	'实现SQL中SELECT操作，传入参数分别为SQL语句，占位符参数集，并返回操作的行数'
	log(sql, args)#调用log()记录SQL操作
	global __pool
	async with __pool.acquire() as conn:#异步获取一个连接
		async with conn.cursor(aiomysql.DictCursor) as cur:#为连接创建游标，并返回dict组成的list，用完自动释放
			await cur.execute(sql.replace('?', '%s'), args or ())#执行SQL操作，SQL语句的占位符是？，MYSQL占位符为%s,在此统一替换为MYSQL占位符
			if size:#如果传入了size参数则只读取size条记录，否则全部读取
				rs = await cur.fetchmany(size)
			else:
				rs = await cur.fetchall()#返回dict组成的list，一个dict代表一行			
		logging.info('rows returned: %s' %len(rs))#显示记录条数
		return rs


async def execute(sql, args, autocommit = True):
	'执行SQL操作：INSERT,UPDATE,DELETE，传入SQL语句、占位符参数集，默认打开MYSQL自动提交事务'
	log(sql, args)
	async with __pool.acquire() as conn:#获取一个连接
		if not autocommit:#如果没有自动提交事务，则启动协程，尝试SQL操作并提交事务
			await conn.begin()
		try:
			async with conn.cursor(aiomysql.DictCursor) as cur:#为连接创建游标，并返回dict组成的list，用完自动释放
				await cur.execute(sql.replace('?', '%s'), args)#执行SQL操作，SQL语句的占位符是？，MYSQL占位符为%s,先替换为MYSQL占位符
				affected = cur.rowcount #获得受操作影响的行数
			if not autocommit:
				await conn.commit()
		except BaseException as e:
			if not autocommit:#如果不是自动提交事务，执行SQL出错时回滚协程并抛出错误
				await conn.rollback() #
			raise
		return affected

def create_args_string(num):
	'产生占位符字符串，生成SQL语句'
	L = []#初始化字符串
	for n in range(num):#插入num个SQL占位符'?'
		L.append('?')#添加操作
	return ','.join(L)#将L拼接成字符串如num=3："?,?,?"

#以下数据库类型类定义中主键指该类型的数据在该列是否是主键，所以赋值为True Or False
class Field(object):
	'定义数据类型基类，用于衍生各种ORM中对应数据库类型的类'
	def __init__(self, name, column_type, primary_key, default):
		'可传入参数对应列名、数据类型、主键、默认值'
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default
	def __str__(self):
		'print(Field_object)时，返回类名Field，数据类型，列名'
		return '<%s, %s: %s>' %(self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
	'从Field继承，定义字符类，对应数据库字符类型，默认变字节长度100'
	def __init__(self, name = None, primary_key = False, default = None, ddl = 'varchar(100)'):
		'可传入参数对应列名、数据类型、主键、默认值'
		super().__init__(name, ddl, primary_key, default)#调用父类进行初始化

class BooleanField(Field):
	'从Field继承，定义布尔类，对应数据库布尔类型'
	def __init__(self, name = None, default = False):
		'可传入参数对应列名、默认值,父类的数据类型和主键直接通过默认值调用父类初始化'
		super().__init__(name, 'boolean', False, default)#调用父类进行初始化

class IngtegerField(Field):
	'从Field继承，定义整数类，对应数据库BIGINT整数类型，默认为0'
	def __init__(self, name = None, primary_key = False, default = 0):
		'可传入参数对应列名、主键、默认值，父类的数据类型直接通过默认值调用父类初始化'
		super().__init__(name, 'bigint', primary_key, default)#调用父类进行初始化

class FloatField(Field):
	'从Field继承，定义浮点类，对应数据库REAL双精度浮点数类型'
	def __init__(self, name = None, primary_key = False, default = 0.0):
		'可传入参数对应列名、主键、默认值，父类的数据类型直接通过默认值调用父类初始化'
		super().__init__(name, 'real', primary_key, default)#调用父类进行初始化

class TextField(Field):
	'从Field继承，定义文本类，对应数据库TEXT长文本数类型'
	def __init__(self, name = None, default = None):
		'可传入参数对应列名、默认值，父类的数据类型和主键直接通过默认值调用父类初始化'
		super().__init__(name, 'text', False, default)#调用父类进行初始化

#定义元类,Metaclass的实例为class，定义的方法也将成为类的方法
class ModelMetaclass(type):
	'定义一个元类，定制类与数据库的映射关系，通ModelMetaclass的子类实现ORM'
	def __new__(cls, name, bases, attrs):#先于__init__运行，用于控制实例产生过程或者配置类，且最后将返回创建的实例,cls类似于self，不过cls指向类而self指向实例。参数对应类名、基类、属性dict
		'用metaclass=ModelMetaclass创建类时，由此方法创建'
		if name == 'Model':#若类名为Model直接返回创建的类，否则
			return type.__new__(cls, name, bases, attrs)
		tableName = attrs.get('__table__', None) or name#获取表名，默认为None，或类的名字
		logging.info('found model: %s (table: %s)' %(name, tableName))#日志显示类名、表名
		mappings = dict()#存储列名及对应的数据类型
		fields = []#存储非主键的列
		primaryKey = None#用于主键查重，做中间暂存，默认为None
		for k, v in attrs.items():#对于attrs中的属性和方法
			if isinstance(v, Field):#如果该属性或方法属于Field类就输出日志并存入mapping中
				logging.info('found mapping: %s ==> %s' %(k, v))
				mappings[k] = v
				if v.primary_key:#主键查重，若首次遇到某个v是主键，则暂存入primaryKey中，再次遇到v为主键则抛出错误
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field: %s' %k)
					primaryKey = k
				else:
					fields.append(k)#如果v不是主键，则存入fields中
		if not primaryKey:#如果没有主键侧报错
			raise RuntimeError('Primary key not found.')
		for k in mappings.keys():#过滤掉Field类的属性，下面会重新放置，改变其位置，专门将Field类的mappings保存在__mappings__中
			attrs.pop(k)
		escaped_fields = list(map(lambda f: '`%s`' %f, fields))#给非主键列加上``区别于字符串
		attrs['__mappings__'] = mappings#存入映射关系
		attrs['__table__'] = tableName#存入表名
		attrs['__primary_key__'] = primaryKey#主键属性名保存在attrs的__primary_key__中，相当于存入主键对应的列
		attrs['__fields__'] = fields#存入非主键
		attrs['__select__'] = 'select %s, %s from %s' %(primaryKey, ','.join(escaped_fields), tableName)#构造SQLselect执行语句，查找整张表
		attrs['__insert__'] = 'insert into %s (%s, %s) value (%s)' %(tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))#构造SQLinsert执行语句，加入占位符，待传入需插入的新数据
		attrs['__update__'] = 'update %s set %s where %s = ?' %(tableName, ','.join(map(lambda f: '%s = ?' %(mappings.get(f).name or f), fields)), primaryKey)#构造SQLupdate执行语句，根据主键值更新对应一行的数据，加入占位符，待传入更新值及主键
		attrs['__delete__'] = 'delete from %s where %s = ?' %(tableName, primaryKey)#构造SQLdelete语句，根据主键删除对应行数据
		return type.__new__(cls, name, bases, attrs)#返回处理后的类

class Model(dict, metaclass = ModelMetaclass):
	'定义对应数据类型的模板类，拥有dict特性及元类的映射关系'
	def __init__(self, **kw):#由于Model没有定义__new__，故将执行父类metaclass的__new__
		super(Model, self).__init__(**kw)#metaclass没有__init__,所以调用父类dict初始化方法进行初始化

	def __getattr__(self, key):
		'根据key实现动态获取'#为什么要动态获取？
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" %key)

	def __setattr__(self, key, value):
		'根据key实现动态绑定'
		self[key] = value
	
	def getValue(self, key):
		'返回属性值，默认为None'
		return getattr(self, key, None)
	
	def getValueOrDefault(self, key):
		'返回属性值，空则返回default默认值'
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' %(key, str(value)))
				setattr(self, key, value)
		return value
	
	@classmethod #添加类方法，类方法的调用不同于实例方法，cls.method(),和cls().method()，默认查找整个表，可通过where limit设置查找条件
	async def findAll(cls, where = None, args = None, **kw):
		'根据where限制条件查表'
		sql = [cls.__select__]#构造sql语句主要部分
		if where:#若有where限制添加限制
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy', None)
		if orderBy:#若关键字中有排序操作则添加
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit', None)
		if limit is not None:#若关键字中有长度限制则添加
			sql.append('limit')
			if isinstance(limit, int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit, tuple) and len (limit) == 2:
				sql.append('?,?')
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value: %s' %str(limit))
		rs = await select(' '.join(sql), args)#调用select执行SQL语句并返回操作记录数
		return [cls(**r) for r in rs]
	
	@classmethod
	async def findNumber(cls, selectField, where = None, args = None):
		'根据where限制用select方法查找表格部分区域'
		sql = ['select %s _num_ from `%s`' %(selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']

	@classmethod
	async def find(cls, pk):
		'根据主键查找实例'
		rs = await select('%s where `%s`=?' %(cls.__select__, cls.__primary_key__), [pk], 1)#调用select根据pk值在表中查找
		if len(rs) == 0:
			return None
		return cls(**rs[0])#类为dict形式，查到主键后返回rs为[{},{}...],得到主键对应的{}后，通过cls产生实例

	async def save(self):
		'映射插入记录'
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = await execute(self.__insert__, args)
		if rows != 1:
			logging.warn('failed to insert record: affected rows: %s' %rows)

	async def update(self):
		'映射更新记录'
		args = list(map(self.getValue, self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = await execute(self.__update__, args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows: %s' %rows)

	async def remove(self):
		'映射删除记录'
		args = [self.getValue(self.__primary_key__)]
		rows = await execute(self.__delete__, args)
		if rows != 1:
			logging.warn('failed to remove by primary key: affected rows: %s' %rows)











