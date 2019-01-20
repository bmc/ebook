FROM ubuntu:17.10

#ENV USERNAME              user
#ENV UID                   1000
#ENV GID                   1000
ENV USERNAME root
ENV UID 0
ENV GID 0

RUN \
  sed -i \
    s/archive\.ubuntu\.com/la-mirrors.evowise.com/g /etc/apt/sources.list && \
  apt-get update && \
  apt-get install --no-install-recommends -y \
    texlive \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-lang-spanish \
    texlive-xetex \
    lmodern \
    ttf-ubuntu-font-family \
    openjdk-8-jre \
    virtualenv python-virtualenv \
    locales \
    plantuml \
    curl && \
  rm -rf /var/lib/apt/lists/*

RUN locale-gen es_AR.UTF-8 && update-locale

RUN curl -LO \
  https://github.com/jgm/pandoc/releases/download/2.0.6/pandoc-2.0.6-1-amd64.deb && \
  dpkg -i pandoc-2.0.6-1-amd64.deb && \
  rm pandoc-2.0.6-1-amd64.deb

#RUN curl -L -o /usr/local/bin/plantuml.jar \
#  http://sourceforge.net/projects/plantuml/files/plantuml.jar/download
#ADD plantuml /usr/local/bin/

#RUN \
#  groupadd --gid ${GID} ${USERNAME} && \
#  useradd --uid ${UID} --gid ${GID} --create-home ${USERNAME}

USER      ${USERNAME}

RUN virtualenv -p python3 /home/${USERNAME}/env

RUN \
  . /home/${USERNAME}/env/bin/activate && \
  curl -L -o /tmp/requirements.txt \
     https://raw.githubusercontent.com/bmc/ebook-template/master/requirements.txt && \
  pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt && \
  pip install WeasyPrint

WORKDIR   /home/${USERNAME}/book
VOLUME    /home/${USERNAME}/book

RUN mkdir -p /usr/local/bin
RUN curl -L -o /usr/local/bin/entrypoint.sh \
  https://raw.githubusercontent.com/bmc/ebook-template/master/docker/entrypoint.sh
RUN sed -i s/USERNAME/${USERNAME}/g /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
