from socket import *
import easygui as eg
import json
import threading
import os
import struct
from pyaudio import PyAudio
HOST = '49.234.220.199'
PORT = 50000
UDPHOST='49.234.220.199'
UDPPORT=50008
UDPADDR = (UDPHOST,UDPPORT)#你想要通信的地址
chatflag = False #是否聊天室聊天
voiceflag = False #是否语音聊天
values = ''
#与服务器建立连接
ADDR = (HOST,PORT)
client_socket = socket(AF_INET,SOCK_STREAM)
client_socket.connect(ADDR)
#聊天线程
class inputdata(threading.Thread):
        def run(self):
                global chatflag
                while True:
                        if chatflag:
                                msg = input()
                                if chatflag:
                                        dataObj = {'title':'msg','msg':msg}
                                        datastr = json.dumps(dataObj)
                                        print("you:",msg)
                                        client_socket.send(datastr.encode('utf-8'))


class getdata(threading.Thread):
        def run(self):
                global chatflag
                while True:
                        if chatflag:
                                try:
                                        data = client_socket.recv(1024).decode('utf-8')
                                        if(data=='msgstop'):
                                                chatflag = False
                                                print(">>>msg room close<<<")
                                        print(data)
                                except:
                                        pass

#语音聊天线程
SAMPLING_RATE = 8000
NUM_SAMPLES = 1024
class player(threading.Thread):
        def __init__(self,stream,conn):
                super(player, self).__init__()
                self.stream = stream
                self.conn = conn
        def run(self):
                while True:
                        if not voiceflag:
                                break
                        try:
                                data,addr = self.conn.recvfrom(2048)
                                self.stream.write(data)#写到stream中，就是从文件中读取数据然后写到声卡里
                        except:
                                pass
class recoder(threading.Thread):
        def __init__(self,stream,conn):
                super(recoder, self).__init__()
                self.stream = stream
                self.conn = conn
        def run(self):
                global UDPADDRno
                global NUM_SAMPLES    #pyaudio内置缓冲大小
                global SAMPLING_RATE  #取样频率
                while True:
                        if not voiceflag:
                                break
                        string_audio_data = self.stream.read(NUM_SAMPLES) 
                        try:
                                self.conn.sendto(string_audio_data,UDPADDR)
                        except:
                                pass

class inputbox(threading.Thread):
        def run(self):
                global values
                values = eg.buttonbox("menu",title="menu",choices=("data","voice call","quit"))
class stopbox(threading.Thread):
        def run(self):
                global voiceflag
                eg.msgbox(msg='stop voice talking', title='', ok_button='STOP')
                voiceflag = False
#界面1，登录、注册、退出
class client(threading.Thread):
        def run(self):
                self.username = ''
                self.password = ''
                self.login_flag = True
                self.onload()
                if self.login_flag:
                        #self.getuserlist()
                        self.userlist = ["refresh","quit"]
                        self.chooseuser()
                client_socket.close()
        def onload(self):
                while True:
                        values = eg.buttonbox("welcome!!!",title="pp",choices=("login","signup","quit"))
                        if values =="quit":
                                self.login_flag = False
                                return False
                        elif values =="login":
                                while True:
                                        values = eg.multpasswordbox("input your name and password", "login", ["username","password"])
                                        self.username = values[0]
                                        self.password = values[1]
                                        #将账号密码发送至服务器，检验是否正确
                                        dataObj = {"title":"login","username":self.username,"password":self.password}
                                        datastr = json.dumps(dataObj)
                                        client_socket.sendall(datastr.encode())
                                        data = client_socket.recv(1024).decode()
                                        if data =="yes":
                                                self.login_flag = True
                                                return True
                                        else:
                                                eg.msgbox(msg='wrong username or password', title='', ok_button='OK')
                        else:
                                while True:
                                        values = eg.multpasswordbox("input your name and password", "login", ["username","password"])
                                        self.username = values[0]
                                        self.password = values[1]
                                        self.password = str(self.password)
                                        values_2 = eg.passwordbox("please confirm your password","confirm")
                                        if self.password == values_2:
                                                #将账号密码发送至服务器，检验是否合理
                                                dataObj = {"title":"signup","username":self.username,"password":self.password}
                                                datastr = json.dumps(dataObj)
                                                client_socket.sendall(datastr.encode())
                                                data = client_socket.recv(1024).decode()
                                                if data =="yes":
                                                        self.login_flag = True
                                                        return True
                                                else:
                                                        eg.msgbox(msg='repeat username!!!', title='', ok_button='OK')
                                        else:
                                                eg.msgbox(msg='inconsistent password', title='', ok_button='OK')
                        
        def getuserlist(self):
                dataObj = {"title":"getuserlist"}
                datastr = json.dumps(dataObj)
                client_socket.sendall(datastr.encode())
                self.userlist = json.loads(client_socket.recv(1024).decode('utf-8'))
                print(">>>get userlist success!!!<<<")
                print(self.userlist)
                self.userlist.append("refresh")
                self.userlist.append("quit")
        def getfilelist(self):
                dataObj = {"title":"getfilelist"}
                datastr = json.dumps(dataObj)
                client_socket.sendall(datastr.encode())
                data = client_socket.recv(1024).decode('utf-8')
                self.filelist = json.loads(data)
                self.filelist.append("quit")
                print(self.filelist)
        def chooseuser(self):
                #界面2，获取在线用户列表（不包含忙线用户，逻辑未实现）
                values = eg.buttonbox("choose a user online to talk",title=self.username,choices=self.userlist)
                if values == "quit":
                        #退出程序
                        self.closelink()
                        return
                if values == "refresh":
                        self.getuserlist()
                        self.chooseuser()
                else:
                        #向服务器发送欲连接的用户列表
                        dataObj = {"title":"linkto","username":values}
                        datastr = json.dumps(dataObj)
                        client_socket.sendall(datastr.encode())
                        self.chatroom()
        def chatroom(self):
                #界面3，聊天室，文字信息只能在命令行发了，语音聊天或文件传输可以在按钮中选择
                print(">>>msg room start<<<")
                print(">>>you can send or recv msg on cmd<<<")
                global chatflag
                global values
                if not chatflag:
                        inputd = inputdata()
                        getd = getdata()
                        inputd.start()
                        getd.start()
                        chatflag = True
                buttonboxd = inputbox()
                buttonboxd.start()
                buttonboxd.join()
                if values == "quit":
                        self.chooseuser()
                if values == "data":
                        self.datachoose()
                if values == "voice call":
                        self.voicecall()

        def datachoose(self):
                global chatflag
                if chatflag:
                        dataObj = {"title":"datachoose"}
                        datastr = json.dumps(dataObj)
                        client_socket.sendall(datastr.encode())
                values = eg.buttonbox("please choose upload or download",title=self.username,choices=("upload","download","quit"))
                if values == "quit":
                        chatflag = True
                        self.chatroom()
                if values == "upload":
                        self.upload()
                if values == "download":
                        self.download()
        def upload(self):
                filepath = eg.fileopenbox(title='choose file')
                filename = filepath.split("\\")[-1]
                filesize = os.path.getsize(filepath)
                #发起文件上传请求
                dataObj = {"title":"upload"}
                datastr = json.dumps(dataObj)
                client_socket.sendall(datastr.encode())
                #发送文件信息报头长度
                dataObj = {"filename":filename,"filesize":filesize}
                datastr = json.dumps(dataObj)
                dataObj_len = struct.pack('i', len(datastr)) #  将字符串的长度打包
                client_socket.send(dataObj_len)
                #发送报头
                client_socket.send(datastr.encode())
                #确认是否断点续传
                cteflag = False
                data = client_socket.recv(1024).decode()
                print("return data",data)
                existlength = 0
                if data != "new":
                        #已存在源文件，接受源文件现有长度，断点续传
                        existlength = int(data)
                        cteflag = True
                        print(">>>continue send<<<")
                #发送文件内容
                with open(filename, 'rb+') as f:
                        if cteflag:
                                f.seek(existlength)
                        data = f.read()
                        client_socket.sendall(data)
                eg.msgbox(msg='file upload success!', title='', ok_button='OK')
                self.datachoose()
        def download(self):
                self.getfilelist()
                global chatflag
                #chatflag = True
                filelist = self.filelist
                if filelist:
                        #发起下载请求
                        values = eg.buttonbox("choose a file to download",title=self.username,choices=filelist)
                        if values == "quit":
                                self.datachoose()
                        dataObj = {"title":"download","filename":values}
                        datastr = json.dumps(dataObj)
                        client_socket.send(datastr.encode())

                        # 接收报头的长度
                        head_struct = client_socket.recv(4)  
                        if head_struct:
                                print('>>>connected to server!<<<')
                        print(head_struct)
                        head_len = struct.unpack('i', head_struct)[0]  # 解析出报头的字符串大小

                        # 接收长度为head_len的报头内容的信息 (包含文件大小,文件名的内容)
                        data = client_socket.recv(head_len)  
                        print(data.decode('utf-8'))
                        head_dir = json.loads(data.decode('utf-8'))
                        filesize_b = head_dir['filesize']
                        filename = head_dir['filename']

                        # 接收文件内容
                        recv_len = 0
                        recv_mesg = b''
                        f = open(filename, 'wb+')
                        while recv_len < filesize_b:
                                print("download",recv_len/filesize_b,"%")
                                if filesize_b - recv_len > 1024:
                                        recv_mesg = client_socket.recv(1024)
                                        f.write(recv_mesg)
                                        recv_len += len(recv_mesg)
                                else:
                                        recv_mesg = client_socket.recv(filesize_b - recv_len)
                                        recv_len += len(recv_mesg)
                                        f.write(recv_mesg)
                        f.close()
                        eg.msgbox(msg='file download success!', title='', ok_button='OK')
                        self.datachoose()
                else:
                        values = eg.buttonbox("no files",title=self.username,choices=filelist)
        def voicecall(self):
                global voiceflag
                voiceflag = True
                server_socket= socket(AF_INET,SOCK_DGRAM)   #定义socket类型，网络通信，UDP
                pa = PyAudio()
                stream = pa.open(format = pa.get_format_from_width(2),channels = 1,rate = SAMPLING_RATE,output = True,input = True,frames_per_buffer=NUM_SAMPLES)
                thread1 = recoder(stream,server_socket)
                thread2 = player(stream,server_socket)
                thread3 = stopbox()
                thread1.start()
                thread2.start()
                thread3.start()
                print(">>>start voice talk<<<")
                thread1.join()
                thread2.join()
                thread3.join()
                stream.stop_stream()#暂停
                stream.close()#关闭
                pa.terminate()
                print(">>>stop voice talk<<<")
                global chatflag
                chatflag = True
                self.chatroom()
        def closelink(self):
                client_socket.close()
                print("link closed")
                
if __name__ == '__main__':
        _client = client()
        _client.start()
        _client.join()
        