import os
import sys
import logging

def daemonize(pid_file):

    # Fork off the parent process
    pid = os.fork()
    
    # If we are in parent process - save child PID and return True
    # If we are in child process - proceed to next steps
    if pid > 0:
        file = open(pid_file, 'w')
        file.write(str(pid))
        file.close()
        return True
    
    # Change the file mode mask
    os.umask(0)
    
    # Create a new SID for the child process
    os.setsid()
    
    # Change the current working directory
    os.chdir('/')
    
    return False
