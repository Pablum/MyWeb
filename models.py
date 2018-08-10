import time, uuid
from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
	'调用time和伪随机数uuid4组合产生唯一id'
	return '%015d%s000' %(int(time.time()*1000),uuid.uuid4().hex)

class User(Model):
	'定义User类映射MYSQL中的user表'
	__table__ = 'user'#表名赋值
	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')#创建主键
	email = StringField(ddl = 'varchar(50)')#定义用户登录账号为邮箱
	passwd = StringField(ddl = 'varchar(50)')#定义用户密码
	admin = BooleanField() #是否为管理员缺省为false
	name = StringField(ddl = 'varchar(50)')#定义用户名
	image = StringField(ddl = 'varchar(500)')#定义用户头像
	created_at = FloatField(default = time.time)#定义用户创建时间

class Blog(Model):
	'定义Blog类映射MYSQL中的blogs表'
	__table__ = 'blogs'#表名赋值
	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')#创建主键
	user_id = StringField(ddl = 'varchar(50)')#定义用户id
	user_name = StringField(ddl = 'varchar(50)')#定义用户名
	user_image = StringField(ddl = 'varchar(50)')#定义用户图片
	name = StringField(ddl = 'varchar(500)')#定义blog名字
	summary = StringField(ddl = 'varchar(200)')#定义...
	content = TextField()#定义blog文本内容
	created_at = FloatField(default = time.time)#定义blog创建时间

class Comment(Model):
	'定义Comment类映射MYSQL中的comments表'
	__table__ = 'comments'
	id = StringField(primary_key = True, default = next_id, ddl = 'varchar(50)')#创建comment主键
	blog_id = StringField(ddl = 'varchar(50)')#定义blogid
	user_id = StringField(ddl = 'varchar(50)')#定义用户id
	user_name = StringField(ddl = 'varchar(50)')#定义用户名
	user_image = StringField(ddl = 'varchar(500)')#定义用户图片
	content = TextField()#定义comment文本内容
	created_at = FloatField(default = time.time)#定义创建时间
