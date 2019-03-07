FROM ubuntu:17.10

RUN groupadd -g 1001 user
RUN useradd -r -u 1001 -g user --create-home user

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
    python3.7 \
    virtualenv python-virtualenv \
    locales \
    plantuml \
    curl && \
  rm -rf /var/lib/apt/lists/*

RUN locale-gen es_AR.UTF-8 && update-locale

RUN curl -LO \
  https://github.com/jgm/pandoc/releases/download/2.7/pandoc-2.7-1-amd64.deb && \
  dpkg -i pandoc-2.7-1-amd64.deb && \
  rm pandoc-2.7-1-amd64.deb

RUN mkdir -p /usr/local/bin

COPY entrypoint.sh /tmp
RUN sed 's/USERNAME/${USERNAME}/g' </tmp/entrypoint.sh >/usr/local/bin/entrypoint
RUN chmod 755 /usr/local/bin/entrypoint

# This fails, because of stupid SourceForge hosting. So, we just include
# a version of the jar in the repo.
#RUN curl -L -o /usr/local/bin/plantuml.jar \
#  http://sourceforge.net/projects/plantuml/files/plantuml.jar/download
COPY plantuml /usr/local/bin/
COPY plantuml.jar /usr/local/bin/

USER ${USERNAME}

RUN virtualenv -p python3 /home/${USERNAME}/env

RUN \
  . /home/${USERNAME}/env/bin/activate && \
  curl -L -o /tmp/requirements.txt \
     https://raw.githubusercontent.com/bmc/ebook-template/master/requirements.txt && \
  pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt && \
  pip install WeasyPrint

WORKDIR /home/${USERNAME}/book
VOLUME  /home/${USERNAME}/book

ENTRYPOINT ["/usr/local/bin/entrypoint"]
