#!/usr/bin/env python

__author__ = 'Bill Bollenbacher'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.core.exception import ServerError
import time
import gevent
import uuid

class DirectAccessTypes:
    (telnet, vsp, ssh) = range(1, 4)
    
class SessionCloseReasons:
    (agent_closed, client_closed, session_timeout, inactivity_timeout) = range(1, 5)

"""
TELNET server class
"""
    
class TelnetServer(object):

    server_socket = None
    port = None
    ip_address = None
    parent_input_callback = None
    username = None
    token = None
    fileobj = None
    TELNET_PROMPT = 'ION telnet>'
    PORT_RANGE_LOWER = 8000
    PORT_RANGE_UPPER = 8010
    close_reason = SessionCloseReasons.client_closed
    activity_seen = False


    def write(self, text):
        log.debug("TelnetServer.write(): text = " + str(text))
        if self.fileobj:
            self.fileobj.write(text)
            self.fileobj.flush()
            activity_seen = True;
        else:
            log.warning("TelnetServer.write(): no connection yet, can not write text")            

    
    def writeline(self, text):
        """Send a packet with line ending."""
        self.write(text+chr(10))


    def authorized(self, token):
        if token == self.token:
            return True
        else:
            log.debug("entered token =" + token + ", expected token =" + self.token)
            return False
    

    def close_connection(self):
        if self.close_reason != SessionCloseReasons.agent_closed:
            # indicate to agent that connection has been closed
            self.parent_input_callback(self.close_reason)
        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
        except Exception as ex:
            # can happen if telnet client closes session first
            log.debug("TelnetServer.close_connection(): exception caught for socket shutdown:" + str(ex))
        self.server_socket.close()
    

    def exit_handler (self, reason):
        self.close_connection()
        log.debug("TelnetServer.handler(): stopping, " + reason)
    

    def handler(self):
        "The actual service to which the user has connected."
        log.debug("TelnetServer.handler(): starting")
        
        self.fileobj = self.connection_socket.makefile()
        username = None
        token = None
        self.write("Username: ")
        try:
            username = self.fileobj.readline().rstrip('\n\r')
        except EOFError:
            self.exit_handler("lost connection")
            return
        if username == '':
            self.exit_handler("lost connection")
            return
        activity_seen = True;
        self.write("token: ")
        try:
            token = self.fileobj.readline().rstrip('\n\r')
        except EOFError:
            self.exit_handler("lost connection")
            return
        activity_seen = True;
        if not self.authorized(token):
            log.debug("login failed")
            self.writeline("login failed")
            self.exit_handler("login failed")
            return
        self.writeline("connected")   # let telnet client user know they are connected
        while True:
            #self.write(self.TELNET_PROMPT)
            try:
                input_line = self.fileobj.readline()
            except EOFError:
                self.exit_handler("lost connection")
                break
            if input_line == '':
                self.exit_handler("lost connection")
                break
            activity_seen = True;
            log.debug("rcvd: " + input_line)
            log.debug("len=" + str(len(input_line)))
            self.parent_input_callback(input_line.rstrip('\n\r'))
            

    def server_greenlet(self):
        log.debug("TelnetServer.server_greenlet(): started")
        self.connection_socket = None
        try:
            self.server_socket.listen(1)
            self.connection_socket, address = self.server_socket.accept()
        except Exception as ex:
            log.info("TelnetServer.server_greenlet(): exception caught <%s>" %str(ex))
            if self.close_reason != SessionCloseReasons.agent_closed:
                # indicate to parent that connection has been lost
                self.parent_input_callback(self.close_reason)
        else:
            self.handler()
        log.debug("TelnetServer.server_greenlet(): stopping")
        

    def __init__(self, input_callback=None, ip_address=None):
        log.debug("TelnetServer.__init__(): IP address = %s" %ip_address)

        # save callback if specified
        if not input_callback:
            log.warning("TelnetServer.__init__(): callback not specified")
            raise ServerError("TelnetServer.__init__(): callback not specified")
        self.parent_input_callback = input_callback
        
        # save ip address if specified
        if not ip_address:
            log.warning("TelnetServer.__init__(): IP address not specified")
            raise ServerError("TelnetServer.__init__(): IP address not specified")
        self.ip_address = ip_address
        
        # search for available port
        self.port = self.PORT_RANGE_LOWER
        self.server_socket = gevent.socket.socket()
        self.server_socket.allow_reuse_address = True
        while True:
            try:
                log.debug("trying to bind to port %s on %s" %(str(self.port), self.ip_address))
                self.server_socket.bind((self.ip_address, self.port))
                break
            except Exception as ex:
                log.debug("exception caught for socket bind:" + str(ex))
                self.port = self.port + 1
                if self.port > self.PORT_RANGE_UPPER:
                    log.warning("TelnetServer.__init__(): no available ports for server")
                    raise ServerError("TelnetServer.__init__(): no available ports")
                    return

        # create token
        self.token = str(uuid.uuid4()).upper()
        
        log.debug("TelnetServer.__init__(): starting server greenlet")
        self.server = gevent.spawn(self.server_greenlet)
        

    def get_connection_info(self):
        return self.port, self.token


    def any_activity(self):
        if self.activity_seen:
            # re-arm the activity detector
            self.activity_seen = False
            return True
        return False
    
    
    def stop(self, reason=None):
        log.debug("TelnetServer.stop()")
        if (reason):
            self.close_reason = reason
        if self.connection_socket:
            # telnet connection has been made
            try:
                self.connection_socket.shutdown(gevent.socket.SHUT_RDWR)
            except Exception as ex:
                # can happen if telnet client closes session first
                log.debug("TelnetServer.stop(): exception caught for socket shutdown: " + str(ex))
            gevent.sleep(.2)
            try:
                self.server.kill()
            except Exception as ex:
                # can happen if telnet client closes session first
                log.debug("TelnetServer.stop(): exception caught for server kill: " + str(ex))
        self.server_socket.close()
        del self.server_socket
            

    def send(self, data):
        # send data from parent to telnet server process to forward to client
        log.debug("TelnetServer.send(): data = " + str(data))
        self.write(data)
        

class DirectAccessServer(object):
    """
    Class for direct access server that interfaces to an IA ResourceAgent
    """
    
    server = None
    
    def __init__(self, 
                 direct_access_type=None, 
                 input_callback=None, 
                 ip_address=None,
                 session_timeout=None,
                 inactivity_timeout=None):
        log.debug("DirectAccessServer.__init__()")

        if not direct_access_type:
            log.warning("DirectAccessServer.__init__(): direct access type not specified")
            raise ServerError("DirectAccessServer.__init__(): direct access type not specified")

        if not input_callback:
            log.warning("DirectAccessServer.__init__(): callback not specified")
            raise ServerError("DirectAccessServer.__init__(): callback not specified")
               
        if not ip_address:
            log.warning("DirectAccessServer.__init__(): IP address not specified")
            raise ServerError("DirectAccessServer.__init__(): IP address not specified")
               
        if not session_timeout:
            log.warning("DirectAccessServer.__init__(): session timeout not specified")
            raise ServerError("DirectAccessServer.__init__(): session timeout not specified")
               
        if not inactivity_timeout:
            log.warning("DirectAccessServer.__init__(): inactivity timeout not specified")
            raise ServerError("DirectAccessServer.__init__(): inactivity timeout not specified")
               
        # start the correct server based on direct_access_type
        if direct_access_type == DirectAccessTypes.telnet:
            self.server = TelnetServer(input_callback, ip_address)
        else:
            raise ServerError("DirectAccessServer.__init__(): Unsupported direct access type")

        log.debug("DirectAccessServer.__init__(): starting timer greenlet")
        self.timer = gevent.spawn(self.timer_greenlet, 
                                   session_timeout=session_timeout,
                                   inactivity_timeout=inactivity_timeout)
                
    def timer_greenlet(self, session_timeout, inactivity_timeout):
        log.debug("DirectAccessServer.timer_greenlet(): started - sessionTO=%d, inactivityTO=%d"
                  %(session_timeout, inactivity_timeout))
        session_start_time = inactivity_start_time = time.time()
        while True:
            gevent.sleep(1)
            timenow = time.time()
            if ((timenow - session_start_time) > session_timeout):
                log.debug("DirectAccessServer.timer_greenlet(): session exceeded session timeout of %d"
                          %session_timeout)
                self.stop(SessionCloseReasons.session_timeout)
                break
            if self.server.any_activity():
                inactivity_start_time = time.time()
            elif ((timenow - inactivity_start_time) > inactivity_timeout):
                log.debug("DirectAccessServer.timer_greenlet(): session exceeded inactivity timeout of %d"
                          %inactivity_timeout)
                self.stop(reason=SessionCloseReasons.inactivity_timeout)
                break
        log.debug("DirectAccessServer.timer_greenlet(): stopped ")
                

    def get_connection_info(self):
        return self.server.get_connection_info()
    
    def stop(self, reason=SessionCloseReasons.agent_closed):
        log.debug("DirectAccessServer.stop()")
        if self.server:
            self.server.stop(reason)
            del self.server
        if self.timer and reason == SessionCloseReasons.agent_closed:
            try:
                self.timer.kill()
            except Exception as ex:
                # can happen if timer already closed session (race condition)
                log.debug("DirectAccessServer.stop(): exception caught for timer kill: " + str(ex))
        
    def send(self, data):
        log.debug("DirectAccessServer.send(): data = " + str(data))
        self.server.send(data)
        
        
        
