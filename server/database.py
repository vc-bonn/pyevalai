# this is a simple rudimentary database to store user and course data inside a pickle file
# In the future, this could be replaced by a SQL database if needed

from markdown2 import Markdown # be careful to use at least 2.4.0 (2.3.8 had a XSS vulnerability!)
import re
import dateutil.parser
from datetime import datetime
from natsort import natsorted
import pickle
from functools import wraps
from copy import deepcopy

def esc(text):
	return tornado.escape.xhtml_escape(text)
pattern = (
	r'((([A-Za-z]{3,9}:(?:\/\/)?)'  # scheme
	r'(?:[\-;:&=\+\$,\w]+@)?[A-Za-z0-9\.\-]+(:\[0-9]+)?'  # user@hostname:port
	r'|(?:www\.|[\-;:&=\+\$,\w]+@)[A-Za-z0-9\.\-]+)'  # www.|user@hostname
	r'((?:\/[\+~%\/\.\w\-_]*)?'  # path
	r'\??(?:[\-\+=&;%@\.\w_]*)'  # query parameters
	r'#?(?:[\.\!\/\\\w]*))?)'  # fragment
	r'(?![^<]*?(?:<\/\w+>|\/?>))'  # ignore anchor HTML tags
	r'(?![^\(]*?\))'  # ignore links in brackets (Markdown links and images)
	)
link_patters = [(re.compile(pattern),r'\1')]
markdown = Markdown(extras=["link-patterns","break-on-newline","tables","fenced-code-blocks","header-ids"],link_patterns=link_patters,safe_mode="escape")
def esc_m(text): # escape markdown
	return markdown.convert(text)

def to_datetime(s): # parse string to datetime
	if s is None:
		return None
	return dateutil.parser.parse(s)

admins = []
users = {}
courses = []

# save / load database
def load_database(filename="server/database.pkl"): # should be called at the very beginning
	global admins, courses, users
	try:
		with open(filename, 'rb') as file:
			admins, users, courses = pickle.load(file)
	except:
		pass

def save_database(filename="server/database.pkl"): # should be called for every modification
	with open(filename, 'wb') as file:
		pickle.dump((admins,users,courses), file)

def update_database(filename="server/database.pkl"): # decorator to save database
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			result = func(*args, **kwargs) # Execute the original function and get its result
			save_database(filename) # Save the state of all arguments passed to the function
			return result
		return wrapper
	return decorator

# user management
@update_database()
def save_user(username,fullname):
	global users
	users[username] = fullname

def get_user(username): # return fullname of user
	if username not in users.keys():
		load_database()
	if username not in users.keys():
		return None
	return users[username]

# admin management
@update_database()
def make_user_admin(user):
	if not is_admin(user):
		admins.append(user)

def is_admin(user):
	return user in admins

# course management
def get_courses():
	return courses

def get_course(course_id):
	c = courses[course_id]
	c["id"] = course_id
	return c

def course_id_by_name(name):
	for i,c in enumerate(courses):
		if name==c["name"]:
			return i
	raise Exception(f"Course {name} does not exist!")

@update_database()
def register_course(name,password=None):
	global courses
	for c in courses:
		if name==c["name"]:
			raise Exception(f"Course {name} already exists!")
	courses.append({
		"name": name,
		"password": password,
		"tutors": [],
		"members": [],
		"exercises": []
		})
	courses = natsorted(courses,key=lambda l:l["name"])

@update_database()
def remove_course(course_id):
	del courses[course_id]

def course_password(course_id):
	courses[course_id]["password"]

# tutor management
@update_database()
def make_user_tutor(course_id,user):
	if not is_tutor(course_id,user):
		courses[course_id]["tutors"].append(user)

def is_tutor(course_id,user):
	return user in courses[course_id]["tutors"]

def is_tutor_courses(user):
	c = []
	for i,course in enumerate(courses):
		if user in course["tutors"]:
			c.append(course)
			c[-1]["id"]=i
	return c

@update_database()
def remove_tutor(course_id,user):
	courses[course_id]["tutors"].remove(user)

# member management
@update_database()
def make_user_member(course_id,user):
	if not is_member(course_id,user):
		courses[course_id]["members"].append(user)

def is_member(course_id,user):
	return user in courses[course_id]["members"]

def is_member_courses(user):
	c = []
	for i,course in enumerate(courses):
		if user in course["members"]:
			c.append(course)
			c[-1]["id"]=i
	return c

@update_database()
def remove_member(course_id,user):
	courses[course_id]["members"].remove(user)

# exercise management
@update_database()
def register_exercise(course_id,ex_name,exercise,solution,points,ex_type="text",tests=[],n_tries=None,deadline=None):
	
	new_exercise = {
		"name": ex_name,
		"exercise": exercise,
		"solution": solution,
		"points": points,
		"ex_type": ex_type, # e.g. "code" or "text"
		"n_tries": n_tries,
		"deadline": to_datetime(deadline),
		"tests": tests,
		"grades": {}, # deprecated => should be removed soon
		"solutions": {}
		}
	
	try:
		ex_id = exercise_id_by_name(course_id,ex_name)
		#new_exercise["grades"] = courses[course_id]["exercises"][ex_id]["grades"] # deprecated
		new_exercise["solutions"] = courses[course_id]["exercises"][ex_id]["solutions"]
		courses[course_id]["exercises"][ex_id] = new_exercise
	except:
		courses[course_id]["exercises"].append(new_exercise)
		courses[course_id]["exercises"] = natsorted(courses[course_id]["exercises"],key=lambda l:l["name"])

def exercise_id_by_name(course_id,name):
	for i,e in enumerate(courses[course_id]["exercises"]):
		if name==e["name"]:
			return i
	raise Exception(f"Exercise {name} does not exist!")

def get_exercises(course_id):
	return courses[course_id]["exercises"]

def get_exercise(course_id,ex_id):
	return courses[course_id]["exercises"][ex_id]

@update_database()
def remove_exercise(course_id,ex_id):
	del courses[course_id]["exercises"][ex_id]

# grade management

# register solution
@update_database()
def register_solution(course_id,ex_id,user,solution):
	"""
	:course_id: course id
	:ex_id: id of exercise
	:user: user name
	:solution: solution provided by user that should be graded
	"""
	if user not in courses[course_id]["exercises"][ex_id]["solutions"].keys():
		courses[course_id]["exercises"][ex_id]["solutions"][user] = []
	
	courses[course_id]["exercises"][ex_id]["solutions"][user].append({
		"solution": solution,
		"timestamp": datetime.now(),
		"grades": []
		})

def still_grading(course_id,ex_id,user):
	"""
	return true, if there is already a handed in solution which is not yet graded, else false
	(if pyevalai is still grading, students should not be able to hand in further solutions to an exercise)
	:course_id: course id
	:ex_id: id of exercise
	:user: user name
	"""
	if user not in courses[course_id]["exercises"][ex_id]["solutions"].keys(): return False # no solutions handed in yet...
	if len(courses[course_id]["exercises"][ex_id]["solutions"][user])==0: return False# no solutions handed in yet... (edge case)
	if len(courses[course_id]["exercises"][ex_id]["solutions"][user][-1]["grades"])>0: return False# solution already graded
	return True


@update_database()
def register_grade(course_id,ex_id,user,solution_id=0,points=0,answer="",messages=[],author=""):
	"""
	:course_id: course id
	:ex_id: id of exercise
	:user: user name
	:solution: solution provided by user that got graded
	:points: points given by ai_grader
	:answer: answer given by ai_grader
	:messages: chat messages of ai_grader (for debugging / background details of grading process)
		wenn messages = [] => Note wurde von Tutor eingetragen
	"""
	if user not in courses[course_id]["exercises"][ex_id]["solutions"].keys(): return
	
	courses[course_id]["exercises"][ex_id]["solutions"][user][-1-solution_id]["grades"].append({
		"points": points,
		"answer": answer,
		"messages": messages, # messages sollten evtl auch noch markdown-escaped werden
		"timestamp": datetime.now(),
		"author": author
		})

def get_graded_exercises(course_id,username):
	exercises = []
	for i,e in enumerate(courses[course_id]["exercises"]):
		exercises.append(deepcopy(e))
		exercises[-1]["id"] = i
		exercises[-1]["student_solution"] = None
		exercises[-1]["grade"] = None
		exercises[-1]["n_attempts"] = 0
		if username in e["solutions"].keys() and len(e["solutions"][username])>0:
			exercises[-1]["student_solution"] = deepcopy(e["solutions"][username][-1])
			exercises[-1]["grade"] = None if len(e["solutions"][username][-1]["grades"])==0 else deepcopy(e["solutions"][username][-1]["grades"][-1])
			exercises[-1]["n_attempts"] = len(e["solutions"][username])
	return exercises

def get_graded_exercise(course_id,exercise_id,username,solution_id=0,grade_id=0):
	ex = deepcopy(courses[course_id]["exercises"][exercise_id])
	ex["student_solution"] = None
	ex["grade"] = None
	ex["n_attempts"] = 0
	ex["n_grades"] = 0
	if username in ex["solutions"].keys() and len(ex["solutions"][username])>0:
		ex["student_solution"] = deepcopy(ex["solutions"][username][-1-solution_id])
		ex["n_grades"] = len(ex["solutions"][username][-1-solution_id]["grades"])
		ex["grade"] = None if ex["n_grades"]==0 else deepcopy(ex["student_solution"]["grades"][-1-grade_id])
		ex["n_attempts"] = len(ex["solutions"][username])
	return ex

def get_grade_table(course_id):
	users = []
	for u in courses[course_id]["members"]:
		users.append({"username":u,"fullname":get_user(u),"grades":[],"sum":0,"sum_worked_on":0})
	exercises = []
	for ex_id,ex in enumerate(courses[course_id]["exercises"]):
		exercises.append(deepcopy(ex))
		exercises[-1]["id"] = ex_id
		for u in users:
			username = u["username"]
			if username in ex["solutions"].keys() and len(ex["solutions"][username])>0:
				n_attempts =len(ex["solutions"][username])
				grade = None if len(ex["solutions"][username][-1]["grades"])==0 else deepcopy(ex["solutions"][username][-1]["grades"][-1])
				checked_solutions = map(lambda sol: len(sol["grades"])>1,ex["solutions"][username])
				all_checked = all(checked_solutions)
				any_checked = any(checked_solutions)
				last_checked = len(ex["solutions"][username][-1]["grades"])>1
				u["grades"].append({"id":ex_id,"grade":grade,"n_attempts":n_attempts,"all_checked":all_checked,"any_checked":any_checked,"last_checked":last_checked})
				u["sum"]+=0 if grade is None else grade["points"]
				u["sum_worked_on"]+=0 if grade is None else exercises[-1]["points"]
			else:
				u["grades"].append({"id":ex_id,"grade":None,"n_attempts":0})
	
	return users, exercises
	

