FROM openjdk:11
COPY --from=python:3.8 / /
COPY ./pdfbox-app-2.0.9.jar /root/pdfbox-app-2.0.23.jar
WORKDIR /home
VOLUME /home
# ENTRYPOINT [ "java", "-jar", "/root/pdfbox-app-2.0.23.jar"]
ENTRYPOINT [ "python3", "/home/run.py"]