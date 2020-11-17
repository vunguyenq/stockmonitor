# base image contains python with pandas
FROM azogue/py36_base:rpi3 
#RUN apt-get update
#RUN apt-get install -y build-essential
RUN pip install --no-cache-dir bs4 gspread oauth2client

#RUN mkdir /home/report

#COPY . /home
#WORKDIR /home
#CMD python /home/hello.py