import socketserver,json
import socket
import struct
import os
import threading
#全局变量
connLst = [] #连接列表，用来保存一个连接的信息（代号 地址和端口 连接对象）
userinfolist = [] #用户注册表
onlineuserlist = [] #在线用户列表
messages = [] #信息缓存
filelist = ["data.txt"] #记录所有上传到服务器的文件名

class Connector(object): #连接对象
    def __init__(self,username,addrPort,conObj):
        self.username = username #账号
        self.addrPort = addrPort #地址及端口
        self.conObj = conObj #TCP连接
        self.linkto = ''


class UDPServer(threading.Thread):
        def __init__(self,conn):
                super(UDPServer, self).__init__()
                self.useraddrlist = []
                self.conn = conn
        def run(self):
                #获取两个用户的地址端口
                while True:
                        msg,addr = self.conn.recvfrom(2048)
                        if addr not in self.useraddrlist:
                                self.useraddrlist.append(addr)
                                print(addr,"joined!")
                                if len(self.useraddrlist)==2:
                                        break
                print(self.useraddrlist)
                ADDR1 = self.useraddrlist[0]
                ADDR2 = self.useraddrlist[1]
                while True:
                        print("connecting")
                        msg,addr = self.conn.recvfrom(2048)
                        if addr == ADDR1:
                                self.conn.sendto(msg,ADDR2)
                        else:
                                self.conn.sendto(msg,ADDR1)
class MyServer(socketserver.BaseRequestHandler): #服务器对象
    def handle(self):
        print("got connection from",self.client_address) #连接建立后self.client_address自动赋值为用户的ip地址
        username='' #用户名
        conobj='' #连接用户对象
        linktoconobj='' #通话对象
        global filelist
        global onlineuserlist
        conn = self.request
        while True:
                data = conn.recv(1024)
                if not data:
                        conn.close()
                        print("close")
                        return
                dataobj = json.loads(data.decode('utf-8'))#将数据转化成json格式
                title = dataobj["title"]
                print(dataobj)
                if title == "login":
                        username = dataobj["username"]
                        password = dataobj["password"]
                        loginflag = False
                        print(username,"login!!!")
                        for item in userinfolist:
                                if item["username"] == username:
                                        if item["password"] == password:
                                                loginflag = True
                                                break
                        if loginflag:
                                conn.sendall('yes'.encode())
                                register = True
                        else:
                                conn.sendall('no'.encode())
                                continue
                        #存储用户对象
                        conobj = Connector(username,self.client_address,self.request)
                        connLst.append(conobj)
                        #在在线用户列表中添加此用户
                        onlineuserlist.append(username)#记得它下线时要把它踢出这个表
                        continue
                if title == "signup":
                        username = dataobj["username"]
                        password = dataobj["password"]
                        loginflag = True
                        for item in userinfolist:
                                if item['username'] == username:
                                        loginflag = False
                                        break
                        if loginflag:
                                conn.sendall('yes'.encode())
                                register = True
                        else:
                                conn.sendall('no'.encode())
                                continue
                        userinfolist.append([username,password])
                        print(username,"signup!!!")
                        #存储用户对象
                        conobj = Connector(username,self.client_address,self.request)
                        connLst.append(conobj)
                        #在在线用户列表中添加此用户
                        onlineuserlist.append(username)#记得它下线时要把它踢出这个表
                        continue
                #获取用户列表
                if title == "getuserlist":
                        datastr = json.dumps(onlineuserlist)
                        conn.sendall(datastr.encode())
                        continue
                #获取用户列表
                if title == "getfilelist":
                        datastr = json.dumps(filelist)
                        conn.sendall(datastr.encode())
                        continue
                #选择通话对象
                if title == "linkto":
                        conobj.linkto = dataobj["username"]
                        for item in connLst:
                                if item.username == dataobj["username"]:
                                        linktoconobj = item
                                        print(linktoconobj.username,linktoconobj.linkto)
                                        break
                        #将缓存信息发入
                        for item in messages:
                                if item.touser == username:
                                        conobj.conObj.sendall(item["msg"].encode("utf-8"))
                                        item = ""
                        continue
                #转发信息
                if title == "msg":
                        #某一用户在文件传输界面和语音通话界面时，另一用户不可以对其发送信息（这个问题可以解决，但是比较麻烦）
                        print(dataobj["msg"])
                        print(username,linktoconobj.username,linktoconobj.linkto)
                        if linktoconobj.linkto == username:
                                linktoconobj.conObj.sendall(dataobj["msg"].encode("utf-8"))
                        else:
                                messages.append({"touser":linktoconobj.username,"msg":dataobj["msg"]})
                if title == "datachoose":
                        conn.sendall('msgstop'.encode('utf-8'))
                if title == "upload":
                        # 发送stop使聊天进程停止
                        # 接收报头的长度
                        head_struct = conn.recv(4)
                        if head_struct:
                                print('已连接服务端,等待接收数据')
                        print(head_struct)
                        head_len = struct.unpack('i', head_struct)[0]  #解析出报头的字符串大小
                        # 接收长度为head_len的报头内容的信息
                        data = conn.recv(head_len) 
                        print(data.decode('utf-8'))
                        head_dir = json.loads(data.decode('utf-8'))
                        filesize_b = head_dir['filesize']
                        filename = head_dir['filename']

                        # 判断是否已经存在文件
                        existflag = False
                        recv_len = 0
                        path = os.getcwd()
                        if filename in os.listdir(path):
                                #存在时发送已经发送的文件长度
                                existflag = True
                                recv_len = os.path.getsize(filename)
                                filesizeexist = str(os.path.getsize(filename))
                                conn.sendall(filesizeexist.encode())
                        else:
                                conn.sendall('new'.encode())

                        # 接收文件内容
                        recv_mesg = b''
                        if existflag:
                                f = open(filename, 'ab')
                        else:
                                f = open(filename, 'wb+')
                        #是否断点测试
                        stopflag = False

                        while recv_len < filesize_b:
                                print("已接收",str(recv_len/filesize_b*100)+"%","大小为",recv_len)
                                if stopflag:
                                        if recv_len/filesize_b>0.5:
                                                break
                                try:
                                        if filesize_b - recv_len > 1024:
                                                recv_mesg = conn.recv(1024)
                                                f.write(recv_mesg)
                                                recv_len += len(recv_mesg)
                                        else:
                                                recv_mesg = conn.recv(filesize_b - recv_len)
                                                recv_len += len(recv_mesg)
                                                f.write(recv_mesg)
                                except:
                                        break
                        print("停止接收")
                        f.close()
                        if stopflag:
                                return
                        filelist.append(filename)
                        print("接收成功")
                if title == "download":
                        filename = dataobj["filename"]
                        filesize = os.path.getsize(filename)
                        dataObj = {"filename":filename,"filesize":filesize}
                        datastr = json.dumps(dataObj)
                        dataObj_len = struct.pack('i', len(datastr)) #  将字符串的长度打包
                        conn.send(dataObj_len)
                        conn.send(datastr.encode())
                        with open(filename, 'rb+') as f:
                                data = f.read()
                                conn.sendall(data)
                        print("downloadsuccess")
class TCPServer(threading.Thread):
        def run(self):
                server = socketserver.ThreadingTCPServer(('172.17.0.10',50000),MyServer)#开启多线程TCP服务器，允许前一连接的handle未结束也可受理新的请求和连接新的客户端
                print('waiting for connection...')
                server.serve_forever()
if __name__ == '__main__':
        thread1 = TCPServer()
        thread1.start()
        UDPHOST='172.17.0.10'
        UDPPORT=50008
        UDPADDR = (UDPHOST,UDPPORT)#你想要通信的地址
        server_socket= socket.socket(socket.AF_INET,socket.SOCK_DGRAM)   #定义socket类型，网络通信，UDP
        server_socket.bind(UDPADDR)
        thread2 = UDPServer(server_socket)
        thread2.start()
        thread1.join()
        thread2.join()