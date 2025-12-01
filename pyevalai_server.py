from tornado.options import define, options
import tornado.ioloop
import tornado.web
import server.database as db
import server.website as website
from server.websocket_server import WebSocketHandler

# hardcode some initial values for database
# (In the future: add a user interface for that...)
db.load_database()
try:
	# register a course (e.g. numerics class etc)
	db.register_course("My course")
except:
	pass
db.make_user_tutor(0,"tutor_username") # assign a tutor to course 0 (in this case: "My course")
db.make_user_tutor(0,"admin_username") # assign a tutor to course 0 (in this case: "My course")
db.make_user_admin("admin_username") # make a user admin => allows to create new / edit existing exercises

# Tornado Application
def make_app(debug=False):
	settings = dict(
		static_path="server/static",
		template_path="server/template",
		include_version=False,
		cookie_secret="MY_COOKIE_SECRET",
		xsrf_cookies=True,
		debug=debug,
		login_url="/login")
	return tornado.web.Application([
		(r"/logout", website.LogoutHandler),
		(r"/login", website.LoginHandler),
		(r"/home", website.HomeHandler),
		(r"/course/(.*)", website.CourseHandler),
		(r"/course_tutor/(.*)", website.CourseTutorHandler),
		(r"/course_csv/(.*)", website.CourseCSVHandler),
		(r"/exercise/(.*)/(.*)/(.*)/(.*)", website.ExerciseHandler),
		(r"/exercise/(.*)/(.*)/(.*)", website.ExerciseHandler),
		(r"/exercise/(.*)/(.*)", website.ExerciseHandler),
		(r"/exercise_tutor/(.*)/(.*)/(.*)/(.*)/(.*)", website.ExerciseTutorHandler),
		(r"/exercise_tutor/(.*)/(.*)/(.*)/(.*)", website.ExerciseTutorHandler),
		(r"/exercise_tutor/(.*)/(.*)/(.*)", website.ExerciseTutorHandler),
		(r"/websocket", WebSocketHandler),
		(r"(.*)", website.HomeHandler),  # WebSocket endpoint => runs on same port as webserver
	],
	default_handler_class=website.My404Handler,**settings),tornado.web.Application([
		("(.*)", website.HTTPRedirectHandler),  # http redirects directly to secure https connection
	],**settings)

if __name__ == "__main__":
	define("https_port", default=443, help="run https server on the given port", type=int)
	define("http_port", default=80, help="run http server on the given port", type=int)
	define("debug", default=False, help="run server in debug mode", type=bool)
	options.parse_command_line()
	
	HTTPSapp,HTTPapp = make_app(debug=options.debug)
	settings = dict( ssl_options={"certfile":"server/certificates/crt.pem","keyfile":"server/certificates/key.pem"})
	HTTPSserver = tornado.httpserver.HTTPServer(HTTPSapp,**settings)
	HTTPSserver.listen(options.https_port)
	HTTPserver = tornado.httpserver.HTTPServer(HTTPapp)
	HTTPserver.listen(options.http_port)
	
	tornado.ioloop.IOLoop.current().start()
