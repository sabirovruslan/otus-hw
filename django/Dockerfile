FROM python:3.6

# set working directory
WORKDIR /usr/src/app

# add requirements (to leverage Docker cache)
ADD requirements.txt .

# install requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD python manage.py migrate && python manage.py runserver 0.0.0.0:8000