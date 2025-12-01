import tornado.web
from server.login import login
import server.database as db
import csv
import io

class HTTPRedirectHandler(tornado.web.RequestHandler):
	def get(self,address):
		self.redirect(f"https://cg2-04.informatik.uni-bonn.de{address}")

class My404Handler(tornado.web.RequestHandler):
	def prepare(self):
		self.set_status(404)
	def get(self):
		self.write("Ups... page not found")

class Authenticated(tornado.web.RequestHandler):
	def get_current_user(self):
		if self.get_secure_cookie('username') is None:
			return False
		
		username = str(self.get_secure_cookie("username"))[2:-1]
		fullname = str(self.get_secure_cookie("fullname"))[2:-1]
		
		return {"username":username,"fullname":fullname}
	
	def render_post(self, string, **kwargs):
		"""
		splitting render() into write(render_string()) leads to more consistent behavior in post methods
		"""
		data = self.render_string(string,**kwargs)
		self.write(data)
	
	def render_from_string(self, string, **kwargs):
		"""
		render from template string (instead of template file)
		:string: template string
		:kwargs: arguments
		:return: rendered string
		"""
		namespace = self.get_template_namespace()
		namespace.update(kwargs,markdown=db.esc_m)
		return Template(string).generate(**namespace).decode('utf-8')
	
	def render_string(self,text,**args):
		return super().render_string(text,**args,markdown=db.esc_m)


class LogoutHandler(Authenticated):
	
	@tornado.web.authenticated
	def get(self):
		self.clear_cookie("username")
		self.clear_cookie("fullname")
		self.redirect("/login")

class LoginHandler(Authenticated):
	
	def get(self):
		if self.get_current_user()!=False:
			self.redirect(self.get_argument("next","/home"))
		else:
			next_arg = self.get_argument("next",None)
			self.render("login.html",next_arg=next_arg)
			
	def post(self):
		next_arg = self.get_argument("next",None)
		username = self.get_body_argument('username')
		password = self.get_body_argument('password')
		
		user_fullname = login(username, password)
		if user_fullname is None:
			self.render("login.html",next_arg=next_arg,alert="username or password incorrect")
			return
		
		else:
			self.set_secure_cookie("username",username)
			self.set_secure_cookie("fullname",user_fullname)
			db.save_user(username,user_fullname)
			self.redirect(self.get_argument("next","/home"))


class HomeHandler(Authenticated):
	
	@tornado.web.authenticated
	def get(self,*args):
		username = self.current_user["username"]
		member_courses = db.is_member_courses(username)
		tutor_courses = db.is_tutor_courses(username)
		
		self.render(f"home.html",user=self.current_user,member_courses=member_courses,tutor_courses=tutor_courses,is_admin=db.is_admin(username))
		

class CourseHandler(Authenticated):
	
	@tornado.web.authenticated
	def get(self,course_id):
		username = self.current_user["username"]
		course_id = int(course_id)
		try:
			if not db.is_member(course_id,username):
				self.redirect("/home")
				return
		except:
			self.redirect("/home")
			return
		
		course = db.get_course(course_id)
		# get exercises and grades
		exercises = db.get_graded_exercises(course_id,username)
		
		max_points,achieved_points = 0,0
		for e in exercises:
			max_points += e["points"]
			if e["grade"] is not None:
				achieved_points += e["grade"]["points"]
		
		self.render(f"course.html",user=self.current_user,course=course,exercises = exercises, max_points=max_points, achieved_points=achieved_points)
		
class CourseTutorHandler(Authenticated):
	
	@tornado.web.authenticated
	def get(self,course_id):
		username = self.current_user["username"]
		course_id = int(course_id)
		try:
			if not db.is_tutor(course_id,username):
				self.redirect("/home")
				return
		except:
			self.redirect("/home")
			return
			
		
		
		course = db.get_course(course_id)
		
		# get all points of all members
		users,exercises = db.get_grade_table(course_id)
		users = sorted(users, key = lambda u: u["username"])
		
		self.render(f"course_tutor.html",user=self.current_user,course=course,course_id=course_id,users=users,exercises = exercises)
		
class CourseCSVHandler(Authenticated):
	
	@tornado.web.authenticated
	def get(self,course_id):
		username = self.current_user["username"]
		course_id = int(course_id)
		try:
			if not db.is_tutor(course_id,username):
				self.redirect("/home")
				return
		except:
			self.redirect("/home")
			return
		
		course = db.get_course(course_id)
		
		# get all points of all members
		users,exercises = db.get_grade_table(course_id)
		
		# create CSV table of achieved points
		output = io.StringIO()
		writer = csv.writer(output)
		
		writer.writerow(["Name","Username"]+[e["name"] for e in exercises])
		for user in users:
			points = []
			for grade in user["grades"]:
				points.append(grade["grade"]["points"] if grade["grade"] is not None else 0)
			writer.writerow([user["fullname"],user["username"]]+points)
		
		# take content from StringIO
		csv_data = output.getvalue()
		output.close()
		
		# set response-Header, to enable download
		self.set_header("Content-Type", "text/csv")
		self.set_header("Content-Disposition", "attachment; filename=data.csv")
		
		# send CSV-Data response
		self.write(csv_data)


class ExerciseHandler(Authenticated):
	
	@tornado.web.authenticated
	def get(self,course_id,exercise_id,solution_id=0,grade_id=0):
		username = self.current_user["username"]
		course_id = int(course_id)
		exercise_id = int(exercise_id)
		solution_id = int(solution_id)
		grade_id = int(grade_id)
		try:
			if not db.is_member(course_id,username):
				self.redirect("/home")
				return
		except:
			self.redirect("/home")
			return
		
		course = db.get_course(course_id)
		course["id"]=course_id
		exercise = db.get_graded_exercise(course_id,exercise_id,username,solution_id,grade_id)
		exercise["id"]=exercise_id
		
		n_exercises = len(db.get_exercises(course_id))
		prev_ex_id = None if exercise_id<=0 else exercise_id-1
		next_ex_id = None if exercise_id>=n_exercises-1 else exercise_id+1
		
		n_solutions = exercise["n_attempts"]
		prev_solution_id = None if solution_id>=n_solutions-1 else solution_id+1
		next_solution_id = None if solution_id<=0 else solution_id-1
		
		n_grades = exercise["n_grades"]
		prev_grade_id = None if grade_id>=n_grades-1 else grade_id+1
		next_grade_id = None if grade_id<=0 else grade_id-1
		
		self.render(f"exercise.html",user=self.current_user,course=course,exercise = exercise,
			  prev_ex_id=prev_ex_id,next_ex_id=next_ex_id,ex_id=exercise_id,solution_id=solution_id,prev_solution_id=prev_solution_id,next_solution_id=next_solution_id,prev_grade_id=prev_grade_id,next_grade_id=next_grade_id)

class ExerciseTutorHandler(Authenticated):
	
	@tornado.web.authenticated
	def get(self,course_id,exercise_id,membername,solution_id=0,grade_id=0):
		username = self.current_user["username"]
		course_id = int(course_id)
		exercise_id = int(exercise_id)
		solution_id = int(solution_id)
		grade_id = int(grade_id)
		try:
			if not db.is_tutor(course_id,username):
				self.redirect("/home")
				return
		except:
			self.redirect("/home")
			return
		
		course = db.get_course(course_id)
		course["id"]=course_id
		exercise = db.get_graded_exercise(course_id,exercise_id,membername,solution_id,grade_id)
		exercise["id"]=exercise_id
		
		n_exercises = len(db.get_exercises(course_id))
		prev_ex_id = None if exercise_id<=0 else exercise_id-1
		next_ex_id = None if exercise_id>=n_exercises-1 else exercise_id+1
		
		members = course["members"]
		member_index = members.index(membername)
		prev_member_name = None if member_index<=0 else members[member_index-1]
		next_member_name = None if member_index>=len(members)-1 else members[member_index+1]
		
		n_solutions = exercise["n_attempts"]
		prev_solution_id = None if solution_id>=n_solutions-1 else solution_id+1
		next_solution_id = None if solution_id<=0 else solution_id-1
		
		n_grades = exercise["n_grades"]
		prev_grade_id = None if grade_id>=n_grades-1 else grade_id+1
		next_grade_id = None if grade_id<=0 else grade_id-1
		
		member = {"username":membername,"fullname":db.get_user(membername)}#TODO
		
		self.render(f"exercise_tutor.html",user=self.current_user,member=member,course=course,exercise = exercise,
			prev_ex_id=prev_ex_id,next_ex_id=next_ex_id,ex_id=exercise_id, prev_member_name=prev_member_name,next_member_name=next_member_name,solution_id=solution_id,prev_solution_id=prev_solution_id,next_solution_id=next_solution_id,prev_grade_id=prev_grade_id,next_grade_id=next_grade_id)
	
	@tornado.web.authenticated
	def post(self,course_id,exercise_id,membername,solution_id=0):
		username = self.current_user["username"]
		course_id = int(course_id)
		exercise_id = int(exercise_id)
		solution_id = int(solution_id)
		
		try:
			if not db.is_tutor(course_id,username):
				self.redirect("/home")
				return
		except:
			self.redirect("/home")
			return
		
		exercise = db.get_graded_exercise(course_id,exercise_id,membername)
		a_points = float(self.get_body_argument('correction_points'))
		answer = f"**{a_points} von {exercise['points']} Punkten**  \n"+self.get_body_argument('correction_text')
		db.register_grade(course_id,exercise_id,membername,solution_id=solution_id,points=a_points,answer=answer,author=username)
		self.redirect(f"/exercise_tutor/{course_id}/{exercise_id}/{membername}/{solution_id}")
		
