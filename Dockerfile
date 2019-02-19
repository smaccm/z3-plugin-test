FROM maven:3.6-jdk-8

ARG img_tag

WORKDIR /root/.m2

RUN echo '<settings>\n\
  <interactiveMode>false</interactiveMode>\n\
  <proxies>\n\
    <proxy>\n\
      <id>secproxy-http</id>\n\
      <active>true</active>\n\
      <protocol>http</protocol>\n\
      <host>secproxy.rockwellcollins.com</host>\n\
      <port>9090</port>\n\
      <nonProxyHosts>localhost|127.0.0.1</nonProxyHosts>\n\
    </proxy>\n\
    <proxy>\n\
      <id>secproxy-https</id>\n\
      <active>true</active>\n\
      <protocol>https</protocol>\n\
      <host>secproxy.rockwellcollins.com</host>\n\
      <port>9090</port>\n\
      <nonProxyHosts>localhost|127.0.0.1</nonProxyHosts>\n\
    </proxy>\n\
    <proxy>\n\
      <id>secproxy-ftp</id>\n\
      <active>true</active>\n\
      <protocol>ftp</protocol>\n\
      <host>secproxy.rockwellcollins.com</host>\n\
      <port>9090</port>\n\
      <nonProxyHosts>localhost|127.0.0.1</nonProxyHosts>\n\
    </proxy>\n\
  </proxies> \n\
</settings>\n\
' >> settings.xml

WORKDIR /root

RUN echo $img_tag > .img_tag.txt

WORKDIR /root/z3-plugin

ENTRYPOINT mvn -X $MVN_OPTIONS install

