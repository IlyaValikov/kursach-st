import json
import logging
from django.views.decorators.csrf import csrf_exempt
import random
import requests
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from channel import settings

fmt = getattr(settings, 'LOG_FORMAT', None)
lvl = getattr(settings, 'LOG_LEVEL', logging.DEBUG)

local_ip = '192.168.1.104'
logging.basicConfig(format=fmt, level=lvl)
logging.debug("Logging started on %s for %s" % (logging.root.name, logging.getLevelName(lvl)))

class ResponseThen(Response):
    def __init__(self,then_callback,request, **kwargs):
        super().__init__(**kwargs)
        self.then_callback = then_callback
        self.request = request
    def close(self):
        super().close()
        logging.debug(self.request)
        self.then_callback(self.request)


@csrf_exempt
@api_view(['Post'])
def code(request):
    def after_return(request):
        syndroms = ['1001','1101','1111','1110','0111','1010','0101','1011','1100','0110','0011','1000','0100','0010','0001'][::-1]
        segmentCode=json.dumps(request,ensure_ascii=False).encode('utf-16')
        byteStr = '1'
        for i in range(0,len(segmentCode),2):
            byteStr+=f'{segmentCode[i+1]:08b}'+f'{(segmentCode[i]):08b}'
            #test+=(chr(int(f'{segmentCode[i+1]:08b}'+f'{(segmentCode[i]):08b}',2)).encode('utf-16', 'surrogatepass').decode('utf-16'))
        byteInt = int(byteStr,2)

        codeByteStr = ''

        #тут происходит кодирование
        for i in range(1,len(byteStr),11):
            #logging.debug(f"{byteStr[i:i+11]:0<11}")
            tmp = f"{byteStr[i:i+11]:0<15}1"[::-1]
            codeByteStr+=f"{byteStr[i:i+11]:0<11}"
            while len(tmp)>5:
                tmp = f'{int(f"{int(tmp,2)^25:b}"[::-1],2):b}'[::-1]
                #logging.debug(f'остаток - {(tmp[::-1])[:-1]:0>4}')
            codeByteStr+=f'{(tmp[::-1])[:-1]:0>4}'
            #logging.debug(codeByteStr)
        logging.debug('кадр закодирован')
        #тут ошибка вносится
        if random.random() <=0.1:
            codeByteStr = f'{int(codeByteStr,2)^2**random.randint(0,len(codeByteStr)-1):b}'
            logging.debug('ошибка внесена')

        
        #тут происходит декодирование
        resByteStr=''
        if random.random() <=0.03:
                logging.debug('потеря кадра')
                return
        for i in range(0,len(codeByteStr),15):
            tmp = f"{codeByteStr[i:i+15]:0<15}1"[::-1]
            while len(tmp)>5:
                tmp = f'{int(f"{int(tmp,2)^25:b}"[::-1],2):b}'[::-1]
            if f"{(tmp[::-1])[:-1]:0>4}"!='0000':
                resByteStr+=f'{int(codeByteStr[i:i+15],2)^2**syndroms.index(f"{(tmp[::-1])[:-1]:0>4}"):0>15b}'[:11]
                logging.debug('ошибка исправлена')
            else:
                resByteStr+=f'{codeByteStr[i:i+11]:0<11}'
                #logging.debug('кусок декодирован без ошибок')
        logging.debug('кадр декодирован')
        #logging.debug(resByteStr[:-(len(resByteStr)%16)]==byteStr[1:])

        #здесь json собирается для отправки на транспортный уровень
        res = ''
        for i in range(0,len(resByteStr)-(len(resByteStr)%16),16):
            res+=(chr(int(resByteStr[i:i+16],2)).encode('utf-16', 'surrogatepass').decode('utf-16'))
        
        #тут запрос на транспортный уровень с исправленным кадром
        logging.debug(json.loads(res.encode('utf-8')))
        resp = requests.post(f'http://{local_ip}:8001/transfer',json=json.loads(res.encode('utf-8')))
        logging.debug(resp.status_code)
        return
        
    logging.debug(request)
    return ResponseThen(after_return,request.data, status=status.HTTP_200_OK)


