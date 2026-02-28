FROM public.ecr.aws/careers360/cnext-backend-base:arm64

ENV PYTHONUNBUFFERED 1

USER root

# Install required system dependencies for Django and Playwright
RUN  apt-get update -y && \
     apt-get install -y gcc-x86-64-linux-gnu g++ libc6-dev unixodbc-dev linux-headers-generic make openssh-client  && \
     apt-get install -y default-libmysqlclient-dev && \
     apt-get install -y libx11-6 libx11-xcb1 libxcomposite1 \
                        libxcursor1 libxdamage1 libxext6 libxi6 libxtst6 \
                        libnss3 libcups2 libxss1 libxrandr2 libasound2 \
                        libatk1.0-0 libatk-bridge2.0-0 libpangocairo-1.0-0 \
                        libgtk-3-0 libgbm1 && \
     rm -rf /var/lib/apt/lists/*

# Configure project
WORKDIR /home/ubuntu/main/zeplin-frontend-validation
COPY requirements.txt /home/ubuntu/main/zeplin-frontend-validation/requirements.txt
RUN pip3 install -r requirements.txt

# Install Playwright Chromium specifically (Zeplin Validator engine)
RUN playwright install chromium

COPY . /home/ubuntu/main/zeplin-frontend-validation

EXPOSE 8080

RUN chmod +x ./deploy/run.bash
ENTRYPOINT ["bash", "./deploy/run.bash"]
