# Setup npm
FROM nikolaik/python-nodejs:latest

WORKDIR "/tools"
ADD . /tools
RUN npm install
RUN npm install uuid
RUN npm install dateformat

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
ENV PATH="/tools:${PATH}"

ENTRYPOINT ["bash"]

