from tornado.options import define, options
import tornado.ioloop
import tornado.web
import tornado.websocket
import json
from server.login import login
import server.database as db
from server.ai_grader import grade_text, grade_code, test_text, test_code
from server.ai import latex_escape, ai_author
import time
import threading
import asyncio
import cloudpickle
import base64
import server.website
from server.certificates.passwords import cookie_secret
from datetime import datetime


# Custom Encoder to Serialize NumPy objects
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return {"__type__": "numpy", "data": base64.b64encode(obj.tobytes()).decode('utf-8'), "dtype": str(obj.dtype), "shape": obj.shape}
        return super().default(obj)

# Decoder to Reconstruct NumPy Objects
def custom_decoder(dct):
    if "__type__" in dct:
        if dct["__type__"] == "numpy":
            data = base64.b64decode(dct["data"])
            return np.frombuffer(data, dtype=dct["dtype"]).reshape(dct["shape"])
    return dct


# WebSocket Handler
class WebSocketHandler(tornado.websocket.WebSocketHandler):
	clients = set()  # Track connected clients
	
	def open(self):
		# Add the client to the set of connected clients
		WebSocketHandler.clients.add(self)
		self.authentified = False
		self.course_id = None
		self.code_test_result = None
		self.code_test_result_condition = threading.Condition()
		self.wait_for_code_test_result = False
		print(f"WebSocket opened: {self.request.remote_ip}")
		self.write_message({"type": "message","value": "Welcome! You are now connected to the server."})
	
	def clear_screen(self, screen=None):
		self.write_message({"type": "clear", "screen": screen})
	
	def unblock(self):
		self.write_message({"type": "unblock"})
	
	def print_md(self, s, screen=None):
		self.write_message({"type": "md","value": s, "screen": screen})
	
	def print_error(self, s, screen=None):
		self.write_message({"type": "error","value": s, "screen": screen})
	
	def print_warn(self, s, screen=None):
		self.write_message({"type": "warn","value": s, "screen": screen})
	
	def print_ok(self, s, screen=None):
		self.write_message({"type": "success","value": s, "screen": screen})
	
	def on_message(self, message):
		# Handle incoming messages from the client
		
		# transform to dict
		msg = json.loads(message)
		
		# check Authentification
		if msg["type"]=="auth":
			username = msg["username"]
			password = msg["password"]
			
			user_fullname = login(username, password)
			if user_fullname is None:
				self.authentified = False
				self.print_error("Authentification failed!")
				return
			
			self.username = username
			self.fullname = user_fullname
			db.save_user(username,user_fullname)
			self.authentified = True
			self.write_message({"type": "clear"})
			self.print_md(f"""### Hallo {self.fullname}!\nEine Übersicht über deine Punkte kannst Du [**>hier<**](https://cg2-04.informatik.uni-bonn.de/home) finden.""")
			self.print_warn("""<strong>Achtung:</strong> AI Grader kann Fehler machen! Frage im Zweifel immer deine Tutoren.""")
			time.sleep(0.1)
			self.unblock()
			print(f"User authentified: {self.fullname} ({self.username})")
			return

		if not self.authentified:
			return
		
		print(f"Received message: {message}")
		
		# Enter course (check, if course exists)
		if msg["type"]=="enter_course":
			
			course = msg["course"]
			try:
				course_id = db.course_id_by_name(course)
			except:
				self.print_error(f"Course '{course}' does not exist!")
				self.unblock()
				return
			
			if db.course_password(course_id) is None and not db.is_member(course_id,self.username):
				db.make_user_member(course_id,self.username)
			
			if not (db.is_member(course_id,self.username) or db.is_tutor(course_id,self.username)):
				self.print_error(f"You are neither a member nor a tutor of '{course_id}'.")
				self.unblock()
				return
			
			self.print_ok(f"Successfully entered '{course}'.")
			self.course_id = course_id
			self.unblock()
			return
		
		# register exercise (only possible with admin rights)
		if msg["type"]=="register_ex":
			
			if self.course_id is None:
				self.print_error(f"Please enter a course before registering exercises!")
				self.unblock()
				return
			
			if not db.is_admin(self.username):
				self.print_error(f"You are not an admin.")
				self.unblock()
				return
			
			name = msg["name"]
			exercise = latex_escape(msg["exercise"])
			solution = latex_escape(msg["solution"])
			points = float(msg["points"])
			ex_type = msg["ex_type"]
			tests = msg["tests"]
			n_tries = msg["n_tries"]
			deadline = msg["deadline"] # TODO: transform to datetime object?
			try:
				db.exercise_id_by_name(self.course_id,name)
				new_ex = False
			except:
				new_ex = True
			db.register_exercise(self.course_id,name,exercise,solution,points,ex_type,tests=tests, n_tries=n_tries, deadline=deadline)
			if new_ex:
				self.print_ok(f"Successfully registered exercise '{name}'")
			else:
				self.print_warn(f"Exercise '{name}' exists already - handed in solutions will be transferred to updated version")
			self.unblock()
			
		
		# delete exercise (only possible with admin rights)
		if msg["type"]=="remove_ex":
			
			if self.course_id is None:
				self.print_error(f"Please enter a course before registering exercises!")
				self.unblock()
				return
			
			if not db.is_admin(self.username):
				self.print_error(f"You are not an admin.")
				self.unblock()
				return
			
			name = msg["name"]
			try:
				ex_id = db.exercise_id_by_name(self.course_id,name)
				db.remove_exercise(self.course_id,ex_id)
				self.print_ok(f"Successfully removed exercise '{name}'")
			except:
				self.print_error(f"Exercise '{name}' does not exist")
			self.unblock()
		
		
		# hand in exercise (as a student)
		if msg["type"]=="handin_ex":
			
			if self.course_id is None:
				self.print_error(f"Please enter a course before handing in exercises!")
				self.unblock()
				return
			
			# check if exercise exists
			ex_name = msg["ex_name"]
			try:
				exercise_id = db.exercise_id_by_name(self.course_id,ex_name)
				exercise = db.get_exercise(self.course_id,exercise_id)
			except:
				self.print_error(f"Exercise {ex_name} does not exist in course {db.get_course(self.course_id)['name']}!")
				self.unblock()
				return
			
			# check if previous submission exercise is currently already being graded...
			if db.still_grading(self.course_id,exercise_id,self.username):
				self.print_warn(f"PyEvalAI is still grading a previos submission!")
				self.unblock()
				return
			
			# check n_tries
			graded_exercise = db.get_graded_exercise(self.course_id,exercise_id,self.username)
			if exercise["n_tries"] is not None:
				attempts_left = exercise['n_tries']-graded_exercise['n_attempts']-1
				if attempts_left<0:
					self.print_error(f"No tries left! You already spend {exercise['n_tries']} tries.")
					self.unblock()
					return
				if attempts_left>1:
					attempts_left_msg = f"Noch {attempts_left} Versuche."
				elif attempts_left==1:
					attempts_left_msg = f"Noch 1 Versuch."
				else:
					attempts_left_msg = f"Keine Versuche mehr."
			
			# check deadline
			if exercise["deadline"] is not None:
				if datetime.now() > exercise["deadline"]:
					self.print_error(f"Deadline already passed ({exercise['deadline']})!")
					self.unblock()
					return
			
			# register solution in database
			solution = latex_escape(msg["solution"])
			if exercise["ex_type"] == "code": solution = f"""```python\n{solution}\n```"""
			db.register_solution(self.course_id,exercise_id,self.username,solution)
			
			answer = f"Aufgabe '{ex_name}' erfolgreich eingereicht! Die Bewertung kann einige Minuten dauern und wird <a href='https://cg2-04.informatik.uni-bonn.de/exercise/{self.course_id}/{exercise_id}'>hier</a> angezeigt."
			if exercise["n_tries"] is not None:
				answer += f" {attempts_left_msg}"
			if exercise["deadline"] is not None:
				answer += f" Deadline: {exercise['deadline']}."
			self.print_ok(answer,screen=exercise["exercise"])
			
			# transform tests
			tests = [] # decoded tests
			for t in exercise["tests"]:
				if t["type"]=="text":
					print(f"test: {t}")
					tests.append(test_text(t["question"],t["yes_points"],t["no_points"]))
				elif t["type"]=="code":
					decoded_test = base64.b64decode(t["encoded_test"])
					deserialized_test = cloudpickle.loads(decoded_test)
					tests.append(test_code(t["question"],deserialized_test))
			
			if exercise["ex_type"] == "text":
				
				def grade_text_thread(exercise,solution,tests):
					asyncio.set_event_loop(asyncio.new_event_loop()) # TODO: is this really needed?!
					print("thread started")
					
					a_points, answer, messages = grade_text(exercise["exercise"], exercise["solution"], solution, exercise["points"],tests, display_steps=True) # this may take a while
					
					answer = latex_escape(answer)
					if exercise["n_tries"] is not None:
						answer += f"  \n**{attempts_left_msg}**"
					
					db.register_grade(self.course_id, exercise_id, self.username, points=a_points, answer=answer, messages=messages, author=ai_author)
					self.clear_screen(screen=ex_name)
					self.print_md(answer,screen=ex_name)
					self.unblock() # TODO: add link to exercise!
				
				
				code_grade_thread = threading.Thread(target=grade_text_thread, args=(graded_exercise,solution,tests))
				code_grade_thread.start()
			
			elif exercise["ex_type"] == "code":
				
				def test_function_caller(*args,**kwargs):
					query = {"type":"test_input","name":ex_name,"args":args,"kwargs":kwargs}
					json_payload = json.dumps(query, cls=CustomEncoder)
					self.write_message(json_payload) # encode x to json
					with self.code_test_result_condition:
						self.wait_for_code_test_result = True
						while self.wait_for_code_test_result: # TODO: check, if this corresponds to ex_name!
							print("waiting for test result")
							self.code_test_result_condition.wait()
					return self.code_test_result
				
				def grade_code_thread(exercise,solution,test_function_caller,tests):
					asyncio.set_event_loop(asyncio.new_event_loop()) # TODO: is this really needed?!
					print("thread started")
					
					a_points, answer, messages = grade_code(exercise["exercise"], exercise["solution"], test_function_caller, solution, exercise["points"], tests, display_steps=True)
					
					answer = latex_escape(answer)
					if exercise["n_tries"] is not None:
						answer += f"  \n**{attempts_left_msg}**"
					
					db.register_grade(self.course_id, exercise_id, self.username, points=a_points, answer=answer, messages=messages, author=ai_author)
					self.clear_screen(screen=ex_name)
					self.print_md(answer,screen=ex_name) # TODO: add link to exercise!
				
				code_grade_thread = threading.Thread(target=grade_code_thread, args=(graded_exercise,solution,test_function_caller,tests))
				code_grade_thread.start()
		
		if msg["type"] == "test_result": # attention: there could be multiple different codes! => create a dict!
			
			msg = json.loads(message, object_hook=custom_decoder)
			self.code_test_result = msg["value"] # decode json
			with self.code_test_result_condition:
				self.wait_for_code_test_result = False
				self.code_test_result_condition.notify()

	def on_close(self):
		# Remove the client from the set of connected clients
		WebSocketHandler.clients.remove(self)
		print(f"WebSocket closed: {self.request.remote_ip}")

	def check_origin(self, origin):
		# Allow connections from any origin (use cautiously in production)
		return True
