import tornado.ioloop
import tornado.websocket
import threading
import time
import getpass
from IPython.display import display, HTML, Markdown
import markdown
import ipywidgets as widgets
import json
import warnings
import cloudpickle
import base64
import inspect
import numpy as np

#########################################################################################
# pyevalai utility functions
#########################################################################################

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

blocking = False
webs = None # websocket
ioloop = None # tornado ioloop
named_screens = {} # for output of specific exercise (dict keys correspond to exercise names)
# names _log and _current are reserved for log screen and current screen
lock = threading.RLock()

test_function = {} # functions that should be evaluated
connect_condition = threading.Condition()

def print_log(s,mode=Markdown):
    print_screen(s,"_log",mode)

def get_screen(screen=None):
    if type(screen) is str: screen = named_screens.get(screen)
    if screen is None or screen=="None": screen = named_screens["_current"]
    return screen

def set_current_screen(name=None):
    global named_screens
    with lock:
      named_screens["_current"] = widgets.Output()
      named_screens["_current"].custom_outputs = []
      display(named_screens["_current"])
      with named_screens["_current"]:
          display(HTML("""<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.6.2/css/bootstrap.min.css">"""))
      if name is not None:
          named_screens[name] = named_screens["_current"]

def set_log_screen():
    set_current_screen("_log")

def clear_screen(screen=None):
    with lock:
      screen = get_screen(screen)
      screen.clear_output(wait=True)
      screen.outputs=[]
      screen.custom_outputs = []
      if screen is not None:
          try:
              with screen:
                display(HTML("""<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.6.2/css/bootstrap.min.css">"""))
          except Exception as e:
              print(f"error while clearing: {e}")
          pass

def print_screen(s,screen=None,mode=Markdown):
    with lock:
      screen = get_screen(screen)
      if screen is not None:
          try:
              with screen:
                  screen.custom_outputs.append({'msg':s,'mode':mode})
                  display(mode(s))
          except Exception as e:
              print(f"error while printing: {e}")
          pass

def refresh_screen(name):
    with lock:
      screen = get_screen(name)
      custom_outputs = [o for o in screen.custom_outputs]
      clear_screen(name)
      for o in custom_outputs:
          print_screen(o["msg"],name,o["mode"])

def refresh_all_screens():
    for name in list(named_screens.keys()):
        refresh_screen(name)

def print_danger(s,screen=None):
    print_screen(f"""<div class="alert alert-block alert-danger">{s}</div>""", screen, HTML)

def print_warn(s,screen=None):
    print_screen(f"""<div class="alert alert-block alert-warning">{s}</div>""", screen, HTML)

def print_ok(s,screen=None):
    print_screen(f"""<div class="alert alert-block alert-success">{s}</div>""", screen, HTML)

def show(s):
    display(Markdown(s))
    return s

def start_client(url="localhost", validate_cert=True):
	global ioloop,webs,blocking
	# Create a new IOLoop for the client thread

	# WebSocket connection callback
	def on_connect(future):
		global webs, connect_condition
		with connect_condition:
			try:
				webs = future.result()  # This gives us the websocket to write messages
			except:
				webs=None
			connect_condition.notify()

	def on_message(message):
		global webs, blocking
		# if message is None => connection closed
		if message is None:
			ioloop.stop()
			print_danger("WebSocket disconnected! login again!")
			blocking = False
			return
		
		msg = json.loads(message)
		
		if msg["type"]=="clear":
			clear_screen(msg.get("screen"))
		
		if msg["type"]=="unblock":
			blocking = False
		
		if msg["type"]=="md":
			print_screen(msg["value"],msg.get("screen"))
		
		if msg["type"]=="error":
			print_danger(msg["value"],msg.get("screen"))
		
		if msg["type"]=="warn":
			print_warn(msg["value"],msg.get("screen"))
		
		if msg["type"]=="success":
			print_ok(msg["value"],msg.get("screen"))
		
		if msg["type"]=="test_input":
			msg = json.loads(message, object_hook=custom_decoder) # decode json
			name = msg["name"]
			input_args = msg["args"]
			input_kwargs = msg["kwargs"]
			try:
				output_value = test_function[name](*input_args,**input_kwargs)
			except Exception as e:
				output_value = None
				print(e)
			
			# encode output_value...
			response = {"type":"test_result","value":output_value}
			json_payload = json.dumps(response, cls=CustomEncoder)
			webs.write_message(json_payload)
		
		return
		

	# Connect to the WebSocket server and use the on_connect callback
	stop_client()
	
	ioloop = tornado.ioloop.IOLoop()
	ws_req = tornado.httpclient.HTTPRequest(f"wss://{url}/websocket", validate_cert=validate_cert) # certificate should always be validated! (Only for debuggin this might be set to false)
	future = tornado.websocket.websocket_connect(ws_req,on_message_callback=on_message)
	future.add_done_callback(on_connect)
	
	# Start the IOLoop for the client thread
	ioloop.start()
	print_log("connection closed")
	blocking = False
	ioloop = None
	webs=None

def stop_client():
	global ioloop, webs
	webs = None
	if ioloop is not None:
		try:
			ioloop.stop()
			ioloop = None
		except:
			print_log("stop_client error")

def start(url="localhost:1234", validate_cert=True):
	global webs, connect_condition
	# Start the client in a separate thread
	for i in range(3): # try at most 3 times to connect
		try:
			client_thread = threading.Thread(target=start_client,args=(url,validate_cert,))
			client_thread.daemon = True  # Ensure the thread exits when the main program exits
			client_thread.start()
			
			start_time = time.time()
			with connect_condition:
				while webs is None and time.time()-start_time<3: # could be done more elegantly with condition variable
					connect_condition.wait(1)
			
			if webs is not None: # connection succeeded
				return
			
			print_log("connection failed ... retry")
		except:
			print_log("could not connect ... retry in 1s")
			time.sleep(1)

def send(msg):
	if webs is None:
		print_danger("WebSocket disconnected! login again!")
		return
	webs.write_message(msg)

def wait_until_unblock():
	global blocking
	while blocking:
		time.sleep(0.2)
	time.sleep(0.2)
	return

#########################################################################################
# user functions
#########################################################################################

def login(url="localhost:1234",username=None,password=None, validate_cert=True, block = True):
	"""
	:url: url of pyevalai server
	:username: username
	:password: password
	:validate_cert: validate SSL certificate (IMPORTANT: this should always remain True for security reasons. Only for debugging on a local server this might be set to False)
	"""
	global blocking
	
	start(url,validate_cert)
	if username is None:
		username = input("Username: ")
	if password is None:
		password = getpass.getpass(prompt="Passwort: ")
	
	set_log_screen()
	
	blocking = True
	send({"type":"auth","username":username,"password":password})
	if block:
		wait_until_unblock()

def enter_course(name):
	set_current_screen()
	send({"type":"enter_course","course":name})

def register_exercise(name,exercise,solution,points,tests=[],ex_type="text",n_tries=None,deadline=None):
	set_current_screen()
	
	send({"type":"register_ex",
	   "name":name,
	   "exercise":exercise,
	   "solution":solution,
	   "points":points,
	   "ex_type":ex_type,
	   "tests":tests,
	   "n_tries":n_tries,
	   "deadline":deadline})

def remove_exercise(name):
	set_current_screen()
	send({"type":"remove_ex", "name":name})

def test_text(question,yes_points=None,no_points=None):
	return [{"type":"text",
		 "question":question,
		 "yes_points":yes_points,
		 "no_points":no_points}]

def test_code(question,unit_test):
	serialized_test = cloudpickle.dumps(unit_test)
	encoded_test = base64.b64encode(serialized_test).decode('utf-8')
	return [{"type":"code",
		 "question":question,
		 "encoded_test":encoded_test}]

def handin_exercise(name,solution, block = True):
	global test_function, exercise_screen, blocking
	set_current_screen(name)
	
	if webs is None:
		print_danger("WebSocket disconnected! login again!","_log")
		return
	
	clear_screen()
	
	if type(solution) != str:
		test_function[name] = solution
		solution = inspect.getsource(solution)
	
	blocking = True
	
	send({"type":"handin_ex",
	   "ex_name":name,
	   "solution":solution})

	if block:
		wait_until_unblock()
