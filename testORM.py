import asyncio
import orm
from models import User, Blog, Comment

async def test(loop):
	await orm.create_pool(user = 'www', password = 'www', db = 'awesome', loop = loop)
	u = User(name = 'Test10', email ='test10@example.com', passwd = '123456', image = 'about:blank')
	await u.save()
	await orm.destroy_pool()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()