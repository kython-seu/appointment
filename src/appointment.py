#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
杭州智慧医疗APP对应的抢号挂号程序.

Usage:
  appointment.py

Created on Apr 5, 2016
@author: wangjinde
"""

import re
import requests
import json
import hashlib
import time
from datetime import datetime

from docopt import docopt


"""
市一：632

普通门诊: 1
专家门诊: 4

jinde card id: 58809
june card id: 27317

产科门诊：1050201

翟洪波：3347，周五
姜文英：2241，周六
夏建妹：3878，周六
吴林珍：6182，周日
王志华：59，周一
李和江：848，周二
江沂：35，周三
徐宁：939，周三
史金凤：2192，周四
林晓峰：279，周四

1-3F门诊B超室：1320501

黄安茜：1052，周五
来蕾：275，周三

皮肤科：1130101
"""

g_department_code = '1050201'
g_clinic_date = '2016-08-18'
g_pri_doc_codes = ['279']
g_prefer_clinic_time = '08:00-08:30'
g_only_pri_docs = True
g_submit = True
g_verbose = False

g_default_schedule_reverse = False


# june's info, card id '27317'. Password can be either text or hashed.
# the password is actually sha256 digest, that can be calculated by "hashlib.sha256(pwd).hexdigest()".
# g_username = '33018319880723262X'
# g_password = '50b9c7460c357fd900fa49b2c50700fe5efae5622025652162e3057eefe8482e'

# jinde's info, card id '58809'
g_username = '331004198502121830'
g_password = 'c714f40f5b9f92a9693dca45932f77cf0365a1e44b36f57eaead0892d6aa7f83'

g_session_id = None


class Appointment(object):
    def __init__(self):
        self.department_code = g_department_code
        self.clinic_date = g_clinic_date
        self.pri_doc_codes = g_pri_doc_codes
        self.only_pri_docs = g_only_pri_docs

        self.username = g_username
        if len(g_password) == 64:
            self.password = g_password
        else:
            self.password = hashlib.sha256(g_password).hexdigest()
        self.card_id = None

        self.session_id = g_session_id

        self.api_url = "http://app.hzwsjsw.gov.cn/api/exec.htm"
        self.headers = {'Accept': 'application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
            'Content-type': 'application/x-www-form-urlencoded;charset=utf-8',
            'Host': 'app.hzwsjsw.gov.cn',
            'Connection': 'Keep-Alive',
            'User-Agent': 'health'}
        self.cookies = None

    def grab_process(self):
        goon = True
        retry_error_limit = 100
        while goon:
            doctors = self.query_doctors_from_scratch()
            requery_doctors = False
            error_time = 0
            while goon and not requery_doctors:
                print(str(datetime.now()))
                for doctor in doctors:
                    print("Query doctor's schedules: ")
                    doctor.print_info()

                    ret_code = self.appointment_with_doctor(doctor)

                    if ret_code == 0:
                        goon = False
                        break
                    elif ret_code == 2:
                        error_time += 1
                        if error_time >= retry_error_limit:
                            requery_doctors = True
                            break

                time.sleep(1)

    def normal_process(self):
        doctors = self.query_doctors_from_scratch()
        if not doctors:
            print("Error: no available doctors.")
            return

        for doctor in doctors:
            print("Query doctor's schedules: ")
            doctor.print_info()

            ret_code = self.appointment_with_doctor(doctor)

            if ret_code == 0:
                break

    def query_doctors_from_scratch(self):
        if not self.session_id:
            # login first
            print("Start login...")
            res_login = self.login_with_hashed_pwd()
            if not res_login:
                print("Failed to login")
                return None

            print('Login success.')
            print('session id: ' + self.session_id)

        print("Query available departments...")
        j = self.query_visible_departments()
        if j is None or int(j['ret_code']) != 0:
            print("Error: query available departments.")
            return None

        print("Query available doctors...")
        return self.query_visible_doctors()

        return doctors

    '''
    ret_code: 0-success, 1-no schedules, 2-error
    '''
    def appointment_with_doctor(self, doctor):
        schedules = self.query_visible_schedules(doctor.doctor_code)
        if schedules is None:
            print("Error: query schedules.")
            return 2
        elif len(schedules) == 0:
            print("No schedules for the doctor.")
            return 1

        print("Schedule count: %d" % (len(schedules)))

        ret_code = 1
        reordered_schedules = self.reorder_schedules(schedules, g_prefer_clinic_time)
        for schedule in reordered_schedules:
            schedule.print_info()
            if g_submit:
                appo_result = self.submit_appointment(schedule)
                if appo_result is not None:
                    print("Succeed:")
                    appo_result.print_info()
                    ret_code = 0
                    break

        return ret_code

    def reorder_schedules(self, schedules, prefer_clinic_time):
        if not prefer_clinic_time:
            # in default order
            if g_default_schedule_reverse:
                reordered_schedules = reversed(schedules)
            else:
                reordered_schedules = schedules
        else:
            reordered_schedules = []
            schedules_count = len(schedules)
            i = 0
            for schedule in schedules:
                if schedule.clinic_time == prefer_clinic_time:
                    break

                i += 1

            if i >= schedules_count:
                # not find
                if g_default_schedule_reverse:
                    reordered_schedules = reversed(schedules)
                else:
                    reordered_schedules = schedules
            else:
                reordered_schedules.extend(schedules[i:schedules_count])
                reordered_schedules.extend(schedules[0:i])

        return reordered_schedules


    def post_request(self, data, headers=None, cookies=None, auto_login=True):
        r = requests.post(self.api_url, data=data, headers=self.headers, cookies=cookies)
        if r.status_code == 200:
            res_content = r.content
            if g_verbose:
                print(res_content)

            j = json.loads(res_content)
            return_code = j['return_code']
            if return_code == 0:
                # keep the cookie
                if (r.cookies and r.cookies['JSESSIONID']):
                    print('Debug: ' + r.cookies['JSESSIONID'])
                    self.cookies = {'JSESSIONID': r.cookies['JSESSIONID']}
                return j['return_params']
            elif return_code == 401 and auto_login:
                print('need relogin...')
                result = self.login_with_hashed_pwd()
                if result == 1:
                    print("auto login success. and resend with new cookies and session id...")
                    print("session id: %s" % self.session_id)
                    new_data, number = re.subn('"session_id":"[a-zA-Z0-9\-_]+"', '"session_id":"%s"' % self.session_id, data)
                    return self.post_request(new_data, headers=headers, cookies=self.cookies, auto_login=False)

        # Error happened
        print('Error: ' + res_content)
        return None

    def login_with_hashed_pwd(self):
        success = False
        data = 'requestData={"api_Channel":"1","client_version":"1.4.6","app_id":"hzpt_android","app_key":"ZW5sNWVWOWhibVJ5YjJsaw==","user_type":"2","api_name":"api.hzpt.user.login","params":{"login_name":"%s","password":"%s","id_card_type":"SFZ"}}' % (self.username, self.password)
        j = self.post_request(data, headers=self.headers)
        if j and int(j['ret_code']) == 0:
            self.session_id = j['session_id']
            success = True

            # get card id if not exist
            if not self.card_id:
                cards = self.parse_json_list(j['card_list'], Card)
                self.card_id = self.parse_and_get_card_id(cards)

        return success

    def query_visible_departments(self):
        data = 'requestData={"api_Channel":"1","client_version":"1.4.6","app_id":"hzpt_android","app_key":"ZW5sNWVWOWhibVJ5YjJsaw==","user_type":"2","api_name":"api.appointment.dept.list","params":{"hospital_id":632,"clinic_date":"%s","clinic_type":"4","page_no":1,"page_size":2147483647},"session_id":"%s"}' % (self.clinic_date, self.session_id)
        return self.post_request(data, headers=self.headers, cookies=self.cookies)

    '''
    i.e. {"return_code":0,"return_msg":"","return_params":{"ret_code":0,
        "list":[{"dept_code":"1050201","dept_name":"产科门诊","doctor_code":"3347","doctor_name":"翟洪波","doctor_position":"主任医师","clinic_date":"2016-08-05","clinic_type":"4"}],
        "ret_info":"成功"}}
    '''
    def query_visible_doctors(self):
        data = 'requestData={"api_Channel":"1","client_version":"1.4.6","app_id":"hzpt_android","app_key":"ZW5sNWVWOWhibVJ5YjJsaw==","user_type":"2","api_name":"api.appointment.doctor.list","params":{"hospital_id":632,"dept_code":"%s","dept_name":"ckmz","page_no":1,"page_size":2147483647},"session_id":"%s"}' % (self.department_code, self.session_id)
        j = self.post_request(data, headers=self.headers, cookies=self.cookies)
        if j and int(j['ret_code']) == 0:
            doctors = self.parse_json_list(j['list'], Doctor)
            return self.filter_reorder_doctors(doctors, self.pri_doc_codes, self.only_pri_docs)

        return None

    def filter_reorder_doctors(self, doctors, pri_list, only_pri_docs):
        if doctors is None or len(doctors) <= 1 or pri_list is None or len(pri_list) == 0:
            return doctors

        # add doctors with priority first
        sorted_doctors = []
        for pri in pri_list:
            f_doctor = self.find_by_doctor_code(doctors, pri)
            if f_doctor:
                sorted_doctors.append(f_doctor)

        if not only_pri_docs:
            # add other doctors
            for doctor in doctors:
                f_doctor = self.find_by_doctor_code(sorted_doctors, doctor.doctor_code)
                if not f_doctor:
                    sorted_doctors.append(doctor)

        return sorted_doctors

    def find_by_doctor_code(self, doctors, doc_code):
        if not doctors or len(doctors) == 0 or not doc_code:
            return None

        for doctor in doctors:
            if doctor.doctor_code == doc_code:
                return doctor

        return None

    def query_visible_schedules(self, doctor_code):
        data = 'requestData={"api_Channel":"1","client_version":"1.4.6","app_id":"hzpt_android","app_key":"ZW5sNWVWOWhibVJ5YjJsaw==","user_type":"2","api_name":"api.appointment.doctor.schedule.new","params":{"hospital_id":632,"dept_code":"%s","doctor_code":"%s","dept_name":"ckmz","page_no":1,"page_size":2147483647},"session_id":"%s"}' % (self.department_code, doctor_code, self.session_id)
        j = self.post_request(data, headers=self.headers, cookies=self.cookies)
        schedules = None
        if j and int(j['ret_code']) == 0:
            schedules = self.parse_json_list(j['list'], Schedule)
        elif j and int(j['ret_code']) == 1:
            # request success but no data.
            schedules = []

        # get card id if not exist
        if not self.card_id:
            cards = self.parse_json_list(j['user_cards'], Card)
            self.card_id = self.parse_and_get_card_id(cards)

        return schedules

    def parse_and_get_card_id(self, cards):
        card_id = None
        if cards:
            for card in cards:
                if 'CITIZEN' == card.card_type.upper():
                    card_id = str(card.card_id)
                    card.print_info()

            if not card_id:
                # not found citizen card, use the first one.
                card_id = str(cards[0].card_id)
                card.print_info()

        return card_id


    '''
    i.e. [{"dept_code":"1050201","dept_name":"产科门诊","doctor_code":"3347","doctor_name":"翟洪波","doctor_position":"主任医师","clinic_date":"2016-08-05","clinic_type":"4"}]
    '''
    def parse_json_list(self, j_doc_list, vo_cls):
        if not j_doc_list:
            return None

        values = []
        for j_doc in j_doc_list:
            value = vo_cls.from_json(j_doc)
            values.append(value)

        return values

    def submit_appointment(self, schedule):
        if not schedule:
            return None

        data = 'requestData={"api_Channel":"1","client_version":"1.4.6","app_id":"hzpt_android","app_key":"ZW5sNWVWOWhibVJ5YjJsaw==","user_type":"2","api_name":"api.appointment.new","params":{"hospital_id":632,"clinic_no":"%s","card_id":%s,"clinic_bc":"%s","clinic_time":"%s"},"session_id":"%s"}' % (schedule.clinic_no, self.card_id, schedule.clinic_bc, schedule.clinic_time, self.session_id)
        j = self.post_request(data, headers=self.headers, cookies=self.cookies)
        if j and int(j['ret_code']) == 0:
            return SuccessAppointment.from_json(j)

        return None

'''
i.e. json representation:
{
    "dept_code": "1130101",
    "dept_name": "皮肤性病科",
    "doctor_code": "227",
    "doctor_name": "陈健",
    "doctor_position": "主治医师",
    "clinic_date": "2016-08-06",
    "clinic_type": "4"
}
'''
class Doctor(object):
    def __init__(self, doctor_name, doctor_code, clinic_date):
        self.doctor_name = doctor_name
        self.doctor_code = doctor_code
        self.clinic_date = clinic_date

    @staticmethod
    def from_json(j):
        if not j:
            return None

        return Doctor(j['doctor_name'], j['doctor_code'], j['clinic_date'])

    def print_info(self):
        print("Doctor code: %s, name: %s, clinic date: %s" % (self.doctor_code, self.doctor_name, self.clinic_date))

    def __eq__(self, other):
        return self.doctor_name == other.doctor_name and self.doctor_code == other.doctor_code and \
               self.clinic_date == other.clinic_date


'''
i.e. json representation:
{
    "clinic_bc": "2",
    "dept_code": "1130101",
    "dept_name": "皮肤性病科",
    "doctor_code": "227",
    "doctor_name": "陈健",
    "clinic_date": "2016-08-06",
    "clinic_type": "4",
    "no": "1",
    "clinic_time": "13:30-14:00",
    "schedule_id": "24009",
    "day_schedule": ""
}
'''
class Schedule(object):
    def __init__(self, schedule_id, no, clinic_time, clinic_bc):
        self.schedule_id = schedule_id
        self.clinic_no = no
        self.clinic_time = clinic_time
        self.clinic_bc = clinic_bc

    @staticmethod
    def from_json(j):
        if not j:
            return None

        return Schedule(j['schedule_id'], j['no'], j['clinic_time'], j['clinic_bc'])

    def print_info(self):
        print("Schdule id: %s, clinic_no: %s, clinic_time: %s, clinic_bc: %s" %
              (self.schedule_id, self.clinic_no, self.clinic_time, self.clinic_bc))

'''
i.e. json representation:
{
    "doctor_name": "陈健",
    "ret_code": 0,
    "clinic_no": "4",
    "dept_name": "皮肤性病科",
    "clinic_time": "13:30-14:00",
    "ret_info": "成功",
    "clinic_date": "2016-08-06",
    "no_pass_word": "376711586"
}
'''
class SuccessAppointment(object):
    def __init__(self, doctor_name, dept_name, clinic_time, clinic_date, no_pass_word):
        self.doctor_name = doctor_name
        self.dept_name = dept_name
        self.clinic_time = clinic_time
        self.clinic_date = clinic_date
        self.no_pass_word = no_pass_word

    @staticmethod
    def from_json(j):
        if not j:
            return None

        return SuccessAppointment(j['doctor_name'], j['dept_name'], j['clinic_time'], j['clinic_date'], j['no_pass_word'])

    def print_info(self):
        print("Success scheduled appointment, ticket: %s, doctor name: %s, department name: %s, clinic date: %s, clinic time: %s" %
              (self.no_pass_word, self.doctor_name, self.dept_name, self.clinic_date, self.clinic_time))


class Card(object):
    def __init__(self, customer_name, card_type, card_no, card_id):
        self.customer_name = customer_name
        self.card_type = card_type
        self.card_no = card_no
        self.card_id = card_id

    @staticmethod
    def from_json(j):
        if not j:
            return None

        return Card(j['customer_name'], j['card_type'], j['card_no'], j['card_id'])

    def print_info(self):
        print("Card info customer name: %s, card type: %s, card no: %s, card id: %s" %
              (self.customer_name, self.card_type, self.card_no, self.card_id))


def main():
    #args = docopt(__doc__)
    #appointment = Appointment(args["USERNAME"], args["PASSWORD"], args["DEPART_CODE"], args["DOCTOR_CODE"])

    appointment = Appointment()
    appointment.grab_process()

if __name__ == "__main__":
    main()