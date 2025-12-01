# PyEvalAI

PyEvalAI is a package for automated evaluations of exercises in python.

## Installation

PyEvalAI can be quickly installed with pip:

```
pip install pyevalai
```

## Quick-Start

If you are a student, here is how to use pyevalai:

```python
from pyevalai import show, login, enter_course, handin_exercise

# login to server with username and password
login(url="server-url")

# enter course (for example numerics)
enter_course("Numerics")

# hand in solution for text exercises
handin_exercise("Exercise 1", "my solution...")

# hand in solution for coding exercises
def f(x):
	return x**2
handin_exercise("Exercise 2", f)
```
