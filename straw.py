from select import select
from socket import *
import argparse
import inspect

LISTEN_CONST = 1024 #number of connections to listen to on the server socket

parser = argparse.ArgumentParser(description=\
'''
Straw is a tiny one-way TCP port forwarder.
If you have machines A,B,C and only B can connect to a
particular port on C, Straw can be used to forward connections from A.
''')
parser.add_argument('--host-port', type=int, help='listening port on the host', required=True)
parser.add_argument('--target-ip', help='target computer ip', required=True)
parser.add_argument('--target-port', type=int, help='target port', required=True)

def server_loop(server_sock, target_addr):
    server_client_dict = {} #keys are connections to us, values are connections to the target
    client_server_dict = {} #inverse to the previous dict
    wlist = {} #the keys are sockets we need to write to on the next iteration, values are data to write
    while True:
        rsocks,wsocks,_ = select(server_client_dict.keys() + server_client_dict.values() + [server_sock], wlist.keys(), [])
        for rs in rsocks:
            if rs is server_sock:
                try:
                    got_ss, got_cs = False, False
                    new_ss, s_addr = server_sock.accept()
                    got_ss = True
                    #Create a new connection:
                    new_cs = socket(AF_INET, SOCK_STREAM)
                    got_cs = True
                    new_cs.connect(target_addr)
                    server_client_dict[new_ss] = new_cs
                    client_server_dict[new_cs] = new_ss
                except Exception, e:
                    if got_ss:
                        del new_ss
                    if got_cs:
                        del new_cs
                    print e
                    print inspect.currentframe().f_lineno
                    pass
            else:
                handle_recv_data(rs, server_client_dict, client_server_dict, wlist)
        for ws in wsocks:
            if ws in client_server_dict:
                dest = client_server_dict[ws]
            else:
                dest = server_client_dict[ws]
            try:
                dest.sendall(wlist[ws])
            except Exception, e:
                print e
                print inspect.currentframe().f_lineno
                do_disconnect(ws, server_client_dict, client_server_dict, wlist)
            del wlist[ws]

def do_disconnect(s, server_client_dict, client_server_dict, wlist):
    try:
        if s in server_client_dict:
            s2 = server_client_dict[s]
            del server_client_dict[s]
            del client_server_dict[s2]
        else:
            s2 = client_server_dict[s]
            del client_server_dict[s]
            del server_client_dict[s2]
        if s2 in wlist:
            del wlist[s2]
        if s in wlist:
            data = wlist[s]
            del wlist[s]
            try:
                s2.sendall(data)
            except Exception, e:
                print e
                print inspect.currentframe().f_lineno
        s2.close()
        s.close()
    except Exception, e:
        print e
        print inspect.currentframe().f_lineno
        pass

def handle_recv_data(rs, server_client_dict, client_server_dict, wlist):
    try:
        data = rs.recv(4096)
        if data == '':
            do_disconnect(rs, server_client_dict, client_server_dict, wlist)
        wlist[rs] = wlist.get(rs,'') + data
    except Exception, e:
        print e
        print inspect.currentframe().f_lineno
        #Error with rs, delete connection:
        do_disconnect(rs, server_client_dict, client_server_dict, wlist)
                
        

def main(args):
    target_addr = args.target_ip, args.target_port
    server_sock = socket(AF_INET, SOCK_STREAM)
    server_sock.bind(('', args.host_port))
    server_sock.listen(LISTEN_CONST)
    server_loop(server_sock, target_addr)

if __name__ == '__main__':
    args = parser.parse_args()
    main(args)

