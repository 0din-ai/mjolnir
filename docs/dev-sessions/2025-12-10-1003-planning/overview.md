# Overview

I would like to build a tool for helping security researchers find LLM jailbreaks in various models. The tool should have the following key features:

* Allow researchers to test different versions of prompts against multiple models using OpenRouter
* In order to test whether a vulnerability worked, it should use the python library documented here: https://github.com/0din-ai/0din-JEF on the model responses
* It should allow users to easily version and switch between different versions of prompts they're working on, and to see which versions of prompts were successful against which models
* The tool should provide a user-friendly interface, possibly a web app, where researchers can input prompts, select models, and view results

Output:

* When a jailbreak is detected, the tool should prepare a report for submission to the 0din Bug Bounty program based on the form here, with all fields filled in: https://0din.ai/vulnerabilities/new
* It should also prepare a JSON object following the structure given in `example-vuln-submission.json`

The tool will be built using Python for the backend, leveraging frameworks such as Flask or Django for the web application. The frontend will be developed using modern web technologies like React or Vue.js to ensure a responsive and intuitive user experience.

