#!/usr/bin/python3
import tornado.web
import tornado.ioloop
import tornado.httpclient
import tornado.gen
import secrets
import os
import hashlib
import string
import json
from tornado.httpclient import HTTPClientError
from pathlib import Path

import o365_creater_class
import o365_creater_auth


Path("./config").mkdir(parents=True, exist_ok=True)

o = o365_creater_class.o365("./config/config_o365.json")

p = o365_creater_auth.pwd("./config/config_pwd.json") #admin login

g = o365_creater_auth.pwd_guest("./config/config_guest.json") #guest login

def protect_info(info_in,protected_keys):
    if type(info_in) == dict:
        return {k:protect_info(v,protected_keys) if (k in protected_keys) else v for k,v in info_in.items()}
    if type(info_in) == list:
        return [protect_info(x, protected_keys) for x in info_in]
    if type(info_in) == str:
        masklen = min(len(info_in) // 5,5)
        return info_in[:masklen] + "...(hidden)..." + info_in[-masklen:len(info_in) if masklen!= 0 else 0] if info_in != "" else ""
    return info_in

class RequestHandlerWithCROS(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(RequestHandlerWithCROS, self).__init__(*args, **kwargs)
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=utf-8")
#        self.set_header("Access-Control-Allow-Origin", "*")
#        self.set_header("Access-Control-Allow-Methods", "*")
#        self.set_header("Access-Control-Allow-Headers", "*")
#    async def options(self, *args, **kwargs): 
#        self.set_header("Access-Control-Allow-Origin", "*")
#        self.set_header("Access-Control-Allow-Methods", "*")
#        self.set_header("Access-Control-Allow-Headers", "*")
#        self.write("OK")

class loginHandler(RequestHandlerWithCROS):
    def __init__(self, *args, **kwargs):
        super(loginHandler, self).__init__(*args, **kwargs)
        self.p = p
        self.g = g
    async def get(self, *args, **kwargs): 
        try:
            get_CAPTCHA = self.get_argument('get_CAPTCHA',  default=False)
            
            if get_CAPTCHA == "p":
                self.write(json.dumps(self.p.getCAPTCHAhtml(),indent=2, ensure_ascii=False))
                return
            elif get_CAPTCHA == "g":
                self.write(json.dumps(self.g.getCAPTCHAhtml(),indent=2, ensure_ascii=False))
                return
            password = self.get_argument('password', True)
            session_id = self.get_argument('session_id', True)
            self.p.checkLoginErr(session_id)
            self.write(json.dumps(self.p.loginUser[session_id], indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

    async def put(self, *args, **kwargs): 
        try:
            password = self.get_argument('password', "")
            password_old = self.get_argument('password_old', "")
            session_id = self.get_argument('session_id', True)
            self.p.checkLoginErr(session_id)
            await self.p.login(password_old,None,checkOnly=True)
            self.p.setPassword(password)
            self.write("OK")
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

    async def post(self, *args, **kwargs): 
        try:
            password = self.get_argument('password', True)
            CAPTCHA = self.get_argument("CAPTCHA", default="")
            ret = await self.p.login(password,CAPTCHA)
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

    async def delete(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            self.p.checkLoginErr(session_id)
            self.p.logout(session_id)
            self.write("OK")
        except HTTPClientError as e:
            print(e)
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class guestloginHandler(loginHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
    def __init__(self, *args, **kwargs):
        super(loginHandler, self).__init__(*args, **kwargs)
        self.p = g

        
        

class CAPTCHAHandler(RequestHandlerWithCROS):
    def __init__(self, *args, **kwargs):
        super(CAPTCHAHandler, self).__init__(*args, **kwargs)
        self.p = p
        self.g = g
    async def get(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            self.p.checkLoginErr(session_id)
            test_func = self.get_argument('test_func',  default=False)
            if test_func == "p":
                test_func_body = self.get_argument('test_func_body',  default="")
                self.write(json.dumps(await self.p.CAPTCHA_verify_api_check("undefined",test_func_body,use_real=False),indent=2, ensure_ascii=False))
                return
            elif test_func == "g":
                test_func_body = self.get_argument('test_func_body',  default="")
                self.write(json.dumps(await self.g.CAPTCHA_verify_api_check("undefined",test_func_body,use_real=False),indent=2, ensure_ascii=False))
                return
            test_req_params = self.get_argument('test_req_params',  default=False)
            if test_req_params == "p":
                test_req_body = json.loads(self.get_argument('test_req_body',  default=""))
                test_ret = await self.p.CAPTCHA_check("undefined",test_req_body)
                test_ret_d = test_ret.__dict__
                test_ret_d["body"] = test_ret.body
                self.write(json.dumps(test_ret_d,indent=2, ensure_ascii=False,default=lambda x:str(x)))
                return
            elif test_req_params == "g":
                test_req_body = json.loads(self.get_argument('test_req_body',  default=""))
                test_ret = await self.g.CAPTCHA_check("undefined",test_req_body)
                test_ret_d = test_ret.__dict__
                test_ret_d["body"] = test_ret.body
                self.write(json.dumps(test_ret_d,indent=2, ensure_ascii=False,default=lambda x:str(x)))
                return
            ret = {
                "p":protect_info(self.p.getCAPTCHAsettings(),["MAIL_smtp_auth_pwd"]),
                "g":protect_info(self.g.getCAPTCHAsettings(),["MAIL_smtp_auth_pwd"]),
            }
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

    async def put(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            self.p.checkLoginErr(session_id)
            new_config =  json.loads(self.request.body)["new_config"]
            self.p.setCAPTCHAsettings(new_config["p"])
            self.g.setCAPTCHAsettings(new_config["g"])
            self.write(json.dumps({"success":True},indent=2, ensure_ascii=False,default=lambda x:str(x)))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class GetPWDHandler(RequestHandlerWithCROS):
    def __init__(self, *args, **kwargs):
        super(GetPWDHandler, self).__init__(*args, **kwargs)
        self.p = p
        self.g = g
    async def post(self, *args, **kwargs): 
        try:
            bkend = self.get_argument('bkend', None)
            email = self.get_argument('email', None)
            CAPTCHA = self.get_argument("CAPTCHA", default="")
            if bkend == "p":
                ret = await self.p.get_pwd_with_CAPTCHA_check(email,CAPTCHA)
            elif bkend == "g":
                ret = await self.g.get_pwd_with_CAPTCHA_check(email,CAPTCHA)
            else:
                raise HTTPClientError(code=400)
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))
        

class setInfoHandler(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            self.write(json.dumps(protect_info(o.__dict__,["secret","client_id","access_token","refresh_token","code"]), indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

    async def put(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            newInfo = self.get_argument('newInfo', True)
            newInfo = json.loads(newInfo)
            o.setInfo(newInfo)
            self.write("OK")
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))


class getSecretIdUrl(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            ret = o.getSecretIdUrl()
            self.write(ret)
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

        
class setSecretHandler(RequestHandlerWithCROS):
    async def put(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            secret = self.get_argument('secret', True)
            client_id = self.get_argument('client_id', True)
            o.setSecret(secret,client_id)
            self.write("OK")
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class getCodeURL(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            ret = o.getCodeURL()
            self.write(ret)
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class setCode(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            code = self.get_argument('code', None)
            error = self.get_argument('error', None)
            error_description = self.get_argument('error_description', None)
            session_state = self.get_argument('session_state', "")
            state = self.get_argument('state', "")
            o.setCode(code,session_state,state,error,error_description)
            self.set_header("Content-Type", "text/html; charset=utf-8")
            self.write('<p style="text-align:center">Finished.<br/>This window will close automatically within <span id="counter">3</span> second(s).</p><script type="text/javascript">function countdown() {var i = document.getElementById("counter"); i.innerHTML = parseInt(i.innerHTML)-1;if (parseInt(i.innerHTML)<=0) { window.close();}}setInterval(function(){ countdown(); },1000);</script>')
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class waitCodeSet(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            old_code_update_time = o.code_update_time
            for wait_sec in range(900):
                if o.code_update_time != old_code_update_time:
                    if o.code_error == None:
                        self.write(json.dumps({"success":True}))
                        return
                    else:
                        raise o.generateError(403,o.code_error,o.code_error_description,)
                else:
                    await tornado.gen.sleep(0.1)   
            raise o.generateError(417,"Timeout","Code not set within 90 seconds")
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class initToken(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            await o.initToken()
            self.write("OK")
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class testInit(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            force = self.get_argument('force', False)
            if force=="true":
                p.checkLoginErr(session_id)#################Need Login if force
                ret = await o.testInit(force=True)
            else:
                ret = await o.testInit()
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class refreshRegInfo(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            ret = await o.refreshRegInfo()
            self.write("OK")
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class setDomainsAndLicences(RequestHandlerWithCROS):
    async def put(self, *args, **kwargs): 
        try:
            session_id = self.get_argument('session_id', True)
            p.checkLoginErr(session_id)#################Need Login
            availableDomains = json.loads(self.get_argument('availableDomains', True))
            availableLicences = json.loads(self.get_argument('availableLicences', True))
            maxAllowedLicense = int(self.get_argument('maxAllowedLicense', 1))
            DEFAULT_usageLocation = self.get_argument('DEFAULT_usageLocation', "US")
            o.setDomainsAndLicences(availableDomains,availableLicences,maxAllowedLicense,DEFAULT_usageLocation)
            self.write("OK")
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))

class getRegInfo(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            guest_session_id = self.get_argument('guest_session_id', True)
            g.checkLoginErr(guest_session_id)################# Guest Login
            ret = o.getRegInfo()
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))
        
class canReg(RequestHandlerWithCROS):
    async def get(self, *args, **kwargs): 
        try:
            guest_session_id = self.get_argument('guest_session_id', True)
            g.checkLoginErr(guest_session_id)################# Guest Login
            username = self.get_argument('userPrincipalName', True).split("@")[0]
            domain =self.get_argument('userPrincipalName', True).split("@")[1]
            ret = await o.canReg(username,domain)
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))
            
class createUser(RequestHandlerWithCROS):
    async def post(self, *args, **kwargs): 
        try:
            guest_session_id = self.get_argument('guest_session_id', True)
            g.checkLoginErr(guest_session_id)################# Guest Login
            userPrincipalName = self.get_argument('userPrincipalName', True)
            displayName = self.get_argument('displayName', True)
            if g.loginUser[guest_session_id].get("userPrincipalName",userPrincipalName) != userPrincipalName:
                raise o.generateError(409,"Conflict","You already created this account: "+ g.loginUser[guest_session_id].get("userPrincipalName") + ", You can't create another one.")
            ret = await o.createUser(userPrincipalName,displayName)
            g.setProperty(guest_session_id,"userPrincipalName",userPrincipalName)
            g.setProperty(guest_session_id,"displayName",displayName)
            g.setProperty(guest_session_id,"regResult",ret)
            g.setProperty(guest_session_id,"redeemed",True)
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))
            
class updateUser(RequestHandlerWithCROS):
    async def put(self, *args, **kwargs): 
        try:
            guest_session_id = self.get_argument('guest_session_id', True)
            g.checkLoginErr(guest_session_id)################# Guest Login
            userPrincipalName = g.loginUser[guest_session_id]["userPrincipalName"]
            infomation = json.loads(self.get_argument('infomation', True))
            ret = await o.updateUser(userPrincipalName,infomation)
            g.setProperty(guest_session_id,"infomation",infomation)
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))
            
class assignLicense(RequestHandlerWithCROS):
    async def post(self, *args, **kwargs): 
        try:
            guest_session_id = self.get_argument('guest_session_id', True)
            g.checkLoginErr(guest_session_id)################# Guest Login
            userPrincipalName = g.loginUser[guest_session_id]["userPrincipalName"]
            addLicensesID = self.get_argument('addLicensesID', "")
            ret = await o.assignLicense(userPrincipalName,addLicensesID)
            g.setProperty(guest_session_id,"addLicensesID",addLicensesID)
            self.write(json.dumps(ret, indent=2, ensure_ascii=False))
        except HTTPClientError as e:
            self.clear()
            self.set_status(e.response.code)
            self.finish(e.response.body)
        except Exception as e:
            self.clear()
            self.set_status(500)
            self.finish(json.dumps({"error":"Internal Error","error_description":str(e)},indent=2, ensure_ascii=False,default=lambda x:str(x)))
        
class MyStaticFileHandler(tornado.web.StaticFileHandler):
    def validate_absolute_path(self, root: str, absolute_path: str):
        root = os.path.abspath(root)
        try:
            return super().validate_absolute_path(root, absolute_path)
        except tornado.web.HTTPError as he:
            if he.status_code == 404:
                return os.path.join(root, self.default_filename)
            else:
                raise he
            


if __name__ == '__main__':
    app = tornado.web.Application(handlers=[
        (r'/api/login', loginHandler),
        (r'/api/guestlogin', guestloginHandler),
        (r'/api/CAPTCHA', CAPTCHAHandler),
        (r'/api/GetPWD', GetPWDHandler),
        (r'/api/Info', setInfoHandler),
        (r'/api/getSecretIdUrl', getSecretIdUrl),
        (r'/api/setSecretId', setSecretHandler),
        (r'/api/getCodeURL', getCodeURL),
        (r'/api/setCode', setCode),
        (r'/api/waitCodeSet', waitCodeSet),
        (r'/api/initToken', initToken),
        (r'/api/testInit', testInit),
        (r'/api/refreshRegInfo', refreshRegInfo),
        (r'/api/setDomainsAndLicences', setDomainsAndLicences),
        (r'/api/getRegInfo', getRegInfo),
        (r'/api/canReg', canReg),
        (r'/api/createUser', createUser),
        (r'/api/updateUser', updateUser),
        (r'/api/assignLicense', assignLicense),
        (r"/(.*)", MyStaticFileHandler, {"path": "o365_uc/dist", "default_filename": "index.html"})
    ])
    server = tornado.httpserver.HTTPServer(app, ssl_options={
           "certfile": os.path.join(os.path.abspath("."), "ssl","server.crt"),
           "keyfile": os.path.join(os.path.abspath("."), "ssl","server.key"),
    })
    server.listen(p.__dict__["listen_port"])
    tornado.ioloop.IOLoop.current().start()
