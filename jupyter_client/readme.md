# PyEvalAI

PyEvalAI is a package for automated evaluations of exercises in Jupyter Notebooks / Google Colab.

## Installation

PyEvalAI can be quickly installed with pip:

```
pip install pyevalai
```

## Quick-Start (Students)

If you are a student, here is how to use pyevalai:

```python
from pyevalai import show, login, enter_course, handin_exercise

# login to server with username and password
login(url="server-url")

# enter course (for example numerics)
enter_course("Numerics")

# hand in solution for text exercises
solution = show("my solution...") # show() displays a string with markdown and Latex
handin_exercise("Exercise 1 (Text)", solution)

# hand in solution for coding exercises
def f(x):
	return x**2
handin_exercise("Exercise 2 (Code)", f)
```

## Quick-Start (Admins)

If you are an administrator, here is how to use pyevalai:

```python
from pyevalai import show, login, enter_course, 

# login to server with username and password
login(url="server-url")

# enter course (for example numerics)
enter_course("Numerics")

# create exemplary exercise that requires a text reply
question = show("what is 2+3?")
solution = show("five")

# register exercise in pyevalai
register_exercise("Exercise 1 (Text)",question,solution,points=2,n_tries=200,deadline="20.12.2026 12:20")


# create exemplary exercise that requires a code reply
question_fibonacci = show(r"""Implement a function f(n) that returns the n-th Fibonacci number!""")
solution_fibonacci = show("""
```python
def f(n):
    \"""
    :n: index for Fibonacci-Number
    :return: n-th Fibonacci Number
    \"""
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
```""")

# create a text unit test (yes / no question with corresponding points)
text_test_ficonacci = test_text("Did the student provide a sufficient code documentation?",yes_points=0.5,no_points=-0.5)

# create a code unit test
# Note: to add code unit tests, this notebook should run in the same environment as the pyevalai_server
# (otherwise there can be code compatibility issues)
def test_f(f):
	"""
	code unit tests can test a provided function f and should return a 'reply string' to the test_code question and optional points that should be considered in the final grade
	"""
    result = ""
    if f(0)!=0:
        result += f"f(0)={f(0)} is incorrect (should be 0)! "
    if f(1)!=1:
        result += f"f(1)={f(1)} is incorrect (should be 1)! "
    if f(3)!=2:
        result += f"f(3)={f(3)} is incorrect (should be 2)! "
    if f(4)!=3:
        result += f"f(4)={f(4)} is incorrect (should be 3)! "
    if result!="":
        return result
    else:
		return "Yes, I tested f(n) for several inputs and the implementation always returned the correct resutls!", 1

code_test_fibonacci = test_code("Does the code always return the correct results for f(n)?",test_f)

# register exercise in pyevalai
register_exercise("Exercise 2 (Code)",question_fibonacci,solution_fibonacci,points=2,tests=text_test_ficonacci+code_test_fibonacci,ex_type="code",n_tries=3,deadline="2026")
```
