# Python Evaluation AI (PyEvalAI)

PyEvalAI is an open-source project that enables fast AI-assisted feedback for Jupyter notebook worksheets while keeping tutors in control of the final grading.

This is the official repository for:  
[PyEvalAI: An Open-Source, Tutor-in-the-Loop System for AI-Assisted Evaluation of Jupyter Notebooks](https://arxiv.org/abs/2502.18425)  
*Nils Wandel, David Stotko, Alexander Schier, Reinhard Klein*, IEEE TALE 2025


## Installation (Client)

If you are a student or an admin, you can install PyEvalAI easily via pip:

```
pip install pyevalai
```

More documentation on the pyevalai client side is provided in the [jupyter_client](jupyter_client/readme.md) folder.

## Installation (Server)

If you are an administrator and want to install a local instance of the pyevalai server, proceed as follows:  

First, download this repository from github:

```
git clone https://github.com/vc-bonn/pyevalai
```

Then create a conda environment from the provided environment.yml file:

```
conda env create -f environment.yml
conda activate env_pyevalai_server
```

Now, you can start the PyEvalAI server by calling:

```
python pyevalai_server.py
```

You can run the server in debug mode by specifying the "--debug=true" flag. Furthermore, you can change the default http and https ports of the server through the "--http_port" and "--https_port" arguments.

The server consists of several components that can / must be adapted to your course or university's individual setting:

- SSL certificates and Cookie Secret
- Login
- LLM API
- Manual setup of courses / admin and tutor rights

### SSL certificates and Cookie Secret
To enable SSL encryption, you should save the corresponding private key and certificate files in the certificates folder and specify the paths in the ssl_options in the pyevalai_server.py file. Furthermore, you should change the cookie_secret.

### Login
To manage access to pyevalai, we rely on the central user management at our university and use the LDAP protocol to verify permissions. 
If your university also supports LDAP, you can adapt the ldap.py file directly for your university's settings. 
If not, you can specify your own login rules by implementing a new login() function in login.py or by filling in login details in the additional_users dict in login.py.

### LLM API
For AI-assisted grading, we employ a local LLM using the text generation inference (TGI) toolkit from huggingface (https://github.com/huggingface/text-generation-inference) and run an AWQ quantized instance of Mistral Large (https://huggingface.co/TechxGenus/Mistral-Large-Instruct-2407-AWQ) on a NVidia A100.

The URL address of the API endpoint and the API key can be specified in the ai.py file. 

If you want to use different models than mistral large, you might also want to specify a different model-related instruction template from the instruction-templates folder.

### Manual setup of courses / admin and tutor rights
In the current implementation, courses have to be added manually in the pyevalai_server.py file (see "db.register_course()"). Tutors can be specified with "db.make_user_tutor()" and admins with "db.make_user_admin()".
In future versions, we plan to provide a userinterface on the pyevalai server for these operations.

## Creating Exercises as an Admin
Admins can create new exercises or modify existing exercises via the pyevalai package in jupyter notebooks. More information is provided inside the [jupyter_client](jupyter_client/readme.md) folder.

## Handing in Solutions as a Student
Students can hand in their solutions via the pyevalai package in jupyter notebooks. More information is provided inside the [jupyter_client](jupyter_client/readme.md) folder. The grades by PyEvalAI will be directly displayed in the jupyter notebook file and can be also checked out on the Pyevalai website.

## AI-assisted grading as a Tutor
To check (and eventually modify) the AI generated grades as a tutor, you can login on the Pyevalai website and enter the corresponding course. Here, a table of all students and exercises shows corresponding points and by clicking on a table entry, a form will pop up that allows to modify a grade.

# Third-Party Packages

This project relies on the following open source third party packages:

- jquery: C0 licence
- katex: MIT licence
- marked: MIT licence



