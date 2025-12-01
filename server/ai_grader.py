# simple solution?
from IPython.display import display, Markdown
import inspect
import getpass
from server.ai import ask,chat,latex_escape,extract_numbers,msg
import numpy as np

def display_chat(messages,n_new=None):
    if n_new is not None:
        messages = messages[-n_new:]
    for message in messages:
        print(f"----------")
        print(f"{message['role']}:")
        print(f"{message['content']}")

def clamp(value,min_value,max_value):
	return max(min(value,max_value),min_value)


def test_text(question,yes_points=None,no_points=None):
	"""
	:question: yes/no question about student solution (if answered with yes, the student should get number of points if points is specified. Ex: "is the conjugate transpose computed correctly?")
	:yes_points: number of points if answer is yes / ja
	:no_points: number of points if answer is no / nein
	"""
	def test_function(messages,f):
		test_messages = chat(messages+msg(question+" Antworte mit 'ja' oder 'nein'!"))
		answer = test_messages[-1]["content"]
		if yes_points is not None and 'ja' in answer.lower():
				return answer, yes_points
		if no_points is not None and 'nein' in answer.lower():
				return answer, no_points
		return answer
	
	return test(question,test_function)

def test_code(question,unit_test):
	return test(question,lambda messages,f: unit_test(f))

def test(question,unit_test):
	"""
	:question: yes/no question about code test (if answered with yes, the student should get number of points if points is specified. Ex: "is f(1)=1 correct?")
	:unit_test: function that takes messages and code-function as input. should return a string that answers the specified question. Optional: additional points that should be considered for the grade
	"""
	return {"question":question,
			"unit_test":unit_test}

def grade_text(exercise,sample_solution,solution,points,tests=[],display_steps=False):
	# TODO: escape lösung von studenten (damit keine [INST]-Anweisungen enthalten sind oder sonstige Überlistungen des Modells)
	
	"""
	# check case for no sensible solution at all
	messages = msg(exercise)+\
			msg(sample_solution,"assistant")+\
			msg("Hier ist die Lösung eines Studenten:\n"+solution+f"\n. Hat sich der Student bereits mit der Aufgabe auseinandergesetzt oder handelt es sich bei der Abgabe nur um einen Platzhalter? Antworte mit 'ja' (ersteres) oder 'nein' (letzteres)!")
	messages = chat(messages)
	if display_steps: display_chat(messages)
	
	if 'nein' in messages[-1]["content"].lower():
		messages = chat(messages+msg("Leider bekommt der Student dann keine Punkte. Schreibe trotzdem eine kurze motivierende Antwort an den Studenten ohne die Lösung zu verraten. Verwende keine Begrüssung!"),answer_start=f"**0 von {points} Punkten** ")
		if display_steps: display_chat(messages,2)
		answer = messages[-1]["content"]
		
		return 0, answer, messages
	"""
	
	# Chat initialisierung # TODO: add "Musterlösung: "
	messages = msg(exercise)+\
			msg(sample_solution,"assistant")+\
			msg("""Hier ist die Lösung eines Studenten:\n"""+solution+"\n")+\
			msg("Ok, ich versuche die Lösung des Studenten im Detail zu verstehen. Wie kann ich dir bei der Korrektur der Lösung des Studenten helfen?","assistant")
	if display_steps: display_chat(messages)
	
	# Test fragen stellen und evtl Teil-Punkte vergeben
	test_answers = []
	test_points = 0
	test_points_available = False
	
	for i,test in enumerate(tests):
		print(test)
		test_result = test["unit_test"](messages,solution)
		
		if type(test_result) is tuple:
			test_points_available = True
			test_points += test_result[1]
			test_result = test_result[0] + f" {test_result[1]} Punkte."
		
		messages = messages+msg("Test-Frage: "+test["question"])+msg(test_result,"assistant")
		if display_steps: display_chat(messages,2)
	
	# Vergleich der Lösung mit der Musterlösung
	messages = chat(messages+msg("""Vergleiche diese Lösung mit der Musterlösung. Gibt es Unterschiede oder Fehler? Bewerte jeweils, ob die Unterschiede vernachlässigbar sind oder ob es sich um gravierende Fehler handelt. Halte dich kurz und fokussiere dich auf wesentliche Fehler z.B. bei Umformungen! Gib hier noch keine Punkte und auch noch keine Gesamtbewertung an!"""))
	if display_steps: display_chat(messages,2)
	
	
	
	# Wurden wichtige Schritte weggelassen? (Ist diese Frage überhaupt nötig?)
	messages = chat(messages+msg("Gibt es wichtige Schritte in der Musterlösung, welche nicht berücksichtigt wurden? Antworte mit 'ja' oder 'nein'!"))
	if display_steps: display_chat(messages,2)
	
	if 'ja' in messages[-1]["content"].lower():
		messages = chat(messages+msg("Welche Schritte aus der Musterlösung wurden nicht berücksichtigt?"))
		if display_steps: display_chat(messages,2)
	
	# Bewertung der Lösung
	if test_points_available:
		tests_msg = f"Berücksichtige dabei die Testfragen, bei denen der Student bereits {test_points} Punkte erhalten hat. "
	elif len(tests)>0:
		tests_msg = f"Berücksichtige dabei auch die Testfragen. "
	else:
		tests_msg = ""
	
	messages = chat(messages+msg(f"Wieviele Punkte von maximal {points} möglichen Punkt(en) sollte der Student für die Lösung bekommen? {tests_msg}Beachte bei der Vergabe der Punkte nur Fehler, welche die Korrektheit der Lösung beeinträchtigen und sei nicht geizig! Fehler in der Notation geben keinen Abzug! Auch etwas unpräzise Formulierungen sollen noch volle Punktzahl geben. Gib nur eine Zahl an! Es dürfen Viertel Punkte vergeben werden."))
	
	if display_steps: display_chat(messages,2)
	a_points = clamp(extract_numbers(messages[-1]["content"])[0],0,points)
	
	# TODO: falls lösung schlecht war, kann antwort auch etwas ausführlicher sein
	messages = chat(messages+msg("Schreibe eine kurze motivierende Antwort an den Studenten, in der Du ihn auf seine erreichten Punkte hinweist! Falls es Abzüge bei der Bewertung gibt, erkläre genau warum anhand der entdeckten Fehler. Halte dich kurz. Erwähne nicht, dass es eine Musterlösung gibt. Verwende keine Begrüssung!"),answer_start=f"**{a_points} von {points} Punkten** ")
	
	
	if display_steps: display_chat(messages,2)
	answer = messages[-1]["content"]
	
	return a_points, answer, messages




def grade_code(exercise,sample_solution,solution,code_solution,points,tests=[],display_steps=False):
	"""
	:exercise: markdown description of exercise (string)
	:sample_solution: markdown description of code solution (string)
	:solution: function of user that solver problem
	:points: points of exercise
	:tests: list of test_text or test_code (im Moment wird nur test_code unterstützt)
	"""
	
	# solution könnte auch Liste von mehreren Funktionen sein? => erstmal vllt nicht nötig...
	# dann lieber mehrere Teilaufgaben machen...
	# zusätzlich eine liste der verwendeten funktionen (hier könnten test-funktionen dabei sein, die für den source code nicht wichtig sind?)
	
	# tests-objekte: fragestellung. Funktion, welche Code entgegennimmt und Antwort-String auf fragestellung zurückgibt. Ausserdem können optional noch Punkte zurückgegeben werden
	points = float(points)
	#code_solution = inspect.getsource(solution) # evtl könnte es mehrere Funktionen geben?
	
	
	"""
	# check case for no sensible solution at all
	messages = msg(exercise)+\
			msg(sample_solution,"assistant")+\
			msg("Hier ist die Lösung eines Studenten:\n```python\n"+code_solution+f"\n```. Hat der Student für diese Abgabe bereits 0.25 Teilpunkte von {points} möglichen Punkten verdient? Beachte bei der Vergabe der Punkte nur Fehler, welche die Korrektheit der Lösung beeinträchtigen und sei nicht geizig! Fehler in der Notation geben keinen Abzug! Auch etwas unpräzise Formulierungen sollen noch volle Punktzahl geben. Antworte mit 'ja' oder 'nein'!")
	messages = chat(messages)
	if display_steps: display_chat(messages)
	
	if 'nein' in messages[-1]["content"].lower():
		messages = chat(messages+msg("Leider bekommt der Student dann keine Punkte. Schreibe trotzdem eine kurze motivierende Antwort an den Studenten ohne die Lösung zu verraten. Verwende keine Begrüssung!"))
		if display_steps: display_chat(messages,2)
		answer = messages[-1]["content"]
		
		return 0, answer, messages
	"""
	
	# Chat initialisierung # TODO: add "Musterlösung: "
	messages = msg(exercise)+\
			msg(sample_solution,"assistant")+\
			msg("""Hier ist die Lösung eines Studenten:\n```python\n"""+code_solution+"\n```")+\
			msg("Ok, ich versuche den Code des Studenten im Detail zu verstehen. Wie kann ich dir bei der Korrektur der Lösung des Studenten helfen?","assistant")
	if display_steps: display_chat(messages)
	
	# Test fragen stellen und evtl Teil-Punkte vergeben
	test_answers = []
	test_points = 0
	test_points_available = False
	
	for i,test in enumerate(tests):
		
		try:
			test_result = test["unit_test"](messages,solution)
			
			if type(test_result) is tuple:
				test_points_available = True
				test_points += test_result[1]
				test_result = test_result[0] + f" {test_result[1]} Punkte."
		except Exception as e:
			print(e)
			test_result = "Test failed! The code is flawed!"
		
		messages = messages+msg("Test-Frage: "+test["question"])+msg(test_result,"assistant")
		if display_steps: display_chat(messages,2)
	
	# Vergleich der Lösung mit der Musterlösung
	messages = chat(messages+msg("""Vergleiche diese Lösung mit der Musterlösung. Gibt es Unterschiede oder Fehler? Bewerte jeweils, ob die Unterschiede vernachlässigbar sind oder ob es sich um gravierende Fehler handelt. Halte dich kurz und fokussiere dich auf wesentliche Fehler z.B. bei Umformungen! Gib hier noch keine Punkte und auch noch keine Gesamtbewertung an!"""))
	if display_steps: display_chat(messages,2)
	
	# Bewertung der Lösung
	if test_points_available:
		tests_msg = f"Berücksichtige dabei die Testfragen, bei denen der Student bereits {test_points} Punkte erhalten hat. "
	elif len(tests)>0:
		tests_msg = f"Berücksichtige dabei auch die Testfragen. "
	else:
		tests_msg = ""
	
	messages = chat(messages+msg(f"Wieviele Punkte von maximal {points} möglichen Punkt(en) sollte der Student für die Lösung bekommen? {tests_msg}Beachte bei der Vergabe der Punkte nur Fehler, welche die Korrektheit der Lösung beeinträchtigen und sei nicht geizig! Fehler in der Notation geben keinen Abzug! Auch etwas unpräzise Formulierungen sollen noch volle Punktzahl geben. Gib nur eine Zahl an! Es dürfen Viertel Punkte vergeben werden."))
	
	if display_steps: display_chat(messages,2)
	a_points = clamp(extract_numbers(messages[-1]["content"])[0],0,points)
	
	# Feedback Generierung (falls lösung schlecht war, kann antwort auch etwas ausführlicher sein)
	messages = chat(messages+msg(f"Schreibe eine kurze motivierende Antwort an den Studenten, in der Du ihn auf seine erreichten Punkte hinweist! Falls es Abzüge bei der Bewertung gibt: erkläre die Abzüge anhand der entdeckten Fehler und gebe Verbesserungsvorschläge. {'Halte dich kurz. ' if a_points>0.7*points else 'Verrate aber nicht die ganze Lösung. '}Erwähne nicht, dass es eine Musterlösung gibt. Verwende keine Begrüssung!"),answer_start=f"**{a_points} von {points} Punkten** ")
	
	if display_steps: display_chat(messages,2)
	answer = messages[-1]["content"]
	
	return a_points, answer, messages
