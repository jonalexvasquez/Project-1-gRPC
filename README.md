This application runs on Python and specifically on Python >=3.7.7. To install Python please follow directions here if 
needed: https://wiki.python.org/moin/BeginnersGuide/Download.

Once python is installed and this repository is pulled follow these steps:

1.) Go to the root of the project and install venv: `python -m venv venv  `

2.) Activate the virtual environment: `source venv/bin/activate`

3.) Install the requirements (gcp libraries): `pip install -r requirements.txt`

4.) Now, in your terminal open up two consoles/sessions of your terminal. First run the server by running: 
`python branch_server.py`. You should see logs stating that certain processes were started.

5.) Now, in your other terminal session run the client: `python client.py`. You will see the results in two places.
The first place you will see the results is in the console itself. The second place you will see the results is in a
file called `output_file.json`. Open that file and you will see the message responses correctly following what was 
the required output.
