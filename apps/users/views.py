from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import make_password
from users.models import UserProfile, EmailVerifyRecord
# 并集运算
from django.db.models import Q
# 基于类实现需要继承的view
from django.views.generic.base import View
from .forms import LoginForm, RegisterForm, ForgetPwdForm, ModifyPwdForm
from utils.email_send import send_register_email

# 实现用户名邮箱均可登录
# 继承ModelBackend类，因为它有方法authenticate，可点进源码查看
class CustomBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 不希望用户存在两个，get只能有一个。两个是get失败的一种原因 Q为使用并集查询
        try:
            # django的后台中密码加密：所以不能password==password
            # UserProfile继承的AbstractUser中有def check_password(self, raw_password):
            user = UserProfile.objects.get(Q(username=username)|Q(email=username))
            if user.check_password(password):
                return user
        except Exception as e:
            return None

'''
注册功能的view
'''
class RegisterView(View):
    def get(self, request):
        # 添加验证码
        register_form = RegisterForm()
        return render(request, 'register.html', {'register_form':register_form})
    def post(self, request):
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            user_name = request.POST.get('email', '')
            if UserProfile.objects.filter(email=user_name):
                return render(request, 'register.html', {'register_form': register_form, 'msg':'用户已存在！'})
            pass_word = request.POST.get('password', '')
            # 实例化一个user_profile对象，将前台值存入
            user_profile = UserProfile()
            user_profile.username = user_name
            user_profile.email = user_name
            # 加密password进行保存
            user_profile.password = make_password(pass_word)
            # 默认激活状态为false
            user_profile.is_active = False
            user_profile.save()
            # 发送注册激活邮件
            send_register_email(email=user_name, send_type='register')
            return render(request, 'login.html', {})
        return render(request, 'register.html', {'register_form': register_form})

'''
登录功能的view
'''
class LoginView(View):
    # 直接调用get方法免去判断
    def get(self, request):
        # render三变量: request 模板名称 一个字典写明传给前端的值
        return render(request, 'login.html', {})
    def post(self, request):
        # 类实例化需要一个字典参数dict:request.POST就是一个QueryDict所以直接传入
        # POST中的usernamepassword，会对应到form中
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            user_name = request.POST.get('username', '')
            pass_word = request.POST.get('password', '')
            # 成功返回user对象,失败返回null
            user = authenticate(username=user_name, password=pass_word)
            if user is not None:
                # login_in 两参数：1.request, 2.user
                # 实际是对request写了一部分东西进去，然后在render的时候：
                # request是要render回去的。这些信息也就随着返回浏览器。完成登录
                if user.is_active:
                    login(request=request, user=user)
                    return render(request, 'index.html', )
                else:
                    return render(request, 'login.html', {'msg': '用户未激活！'})
            else:
                return render(request, 'login.html', {'msg': '用户名或密码错误！'})
        else:
            return render(request, 'login.html', {'login_form': login_form})

'''
激活功能的view
'''
class ActiveUserView(View):
    def get(self, request, active_code):
        # 查询邮箱验证记录是否存在
        all_records = EmailVerifyRecord.objects.filter(code=active_code)
        if all_records:
            for record in all_records:
                # 查找到邮箱对应的user
                user = UserProfile.objects.get(email=record.email)
                user.is_active = True
                user.save()
            # 激活成功跳转到登录页面
            return render(request, 'login.html', {})
        else:
            return render(request, 'active_fail.html')

'''
用户忘记密码的处理view
'''
class ForgetPwdView(View):
    def get(self, request):
        # 添加验证码
        forget_form = ForgetPwdForm()
        return render(request, 'forgetpwd.html', {'forget_form':forget_form})
    def post(self, request):
        forget_form = ForgetPwdForm(request.POST)
        if forget_form.is_valid():
            email = request.POST.get('email','')
            send_register_email(email=email, send_type='forget')
            return render(request, 'send_success.html')
        else:
            return render(request, 'forgetpwd.html', {'forget_form': forget_form})

'''
重置密码的view
'''
class ResetView(View):
    def get(self, request, reset_code):
        # 查询邮箱验证记录是否存在
        all_records = EmailVerifyRecord.objects.filter(code=reset_code)
        if all_records:
            for record in all_records:
                # 将email传回来
                return render(request, 'password_reset.html', {'email':record.email})
        else:
            return render(request, 'active_fail.html')

'''
重置密码页面中，确认密码的表单提交后的View
'''
class ModifyPwdView(View):
    def post(self, request):
        modify_form = ModifyPwdForm(request.POST)
        email = request.POST.get('email', '') # 获取hidden组件post来的邮箱
        if modify_form.is_valid():
            pwd1 = request.POST.get('password1', '')
            pwd2 = request.POST.get('password2', '')
            # 如果两次密码不相等，返回错误信息
            if pwd1 != pwd2:
                return render(request, 'password_reset.html', {'email': email, 'msg':'密码不一致'})
            user = UserProfile.objects.get(email=email)
            # 加密成密文存入password字段中
            user.password = make_password(pwd1)
            user.save()
            return render(request, 'login.html', {'msg':'修改密码成功，请重新登录'})
        else:
            return render(request, 'password_reset.html', {'email': email, 'modify_form':modify_form})