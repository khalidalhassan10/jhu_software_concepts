Module 1 – Personal Website (Flask)
Khaled Al-Hassan

Requirements: Python 3.10 or higher (developed on 3.12), Flask (see requirements.txt)

How to run:
  1. cd module_1
  2. pip install -r requirements.txt
  3. python run.py
  4. Open http://localhost:8080

Pages: Home (/), Projects (/projects), Contact (/contact)

Structure:
  run.py               creates the app and registers the blueprint
  pages/pages.py       blueprint with one route per page
  templates/           home.html, projects.html, contact.html
  static/css/home.css  stylesheet shared by all pages
  static/me.png        homepage photo
  screenshots.pdf      screenshots of each page


Sources and assistance:

Course materials:
  - Module 1 lecture slides and lecture video.
  - Module 1 assignment page: the sample site screenshots were used as the
    layout baseline (nav bar top-right, bio left / photo right).
  - "Set Up GitHub" page (Course Information) for the repository setup.

AI assistance:
  - Claude AI (Anthropic) was used in this project, mostly to draft the HTML templates 
    and the CSS but also to help in .py files. All code was reviewed, edited, and tested by me.