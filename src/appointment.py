#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Upload photos and save the photo count for each user in a property file.

Usage:
  appointment.py

Created on Apr 5, 2016
@author: wangjinde
"""

import sys
import os
import re
import requests
import json
import urllib

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
"""
class Appointment(object):
    def __init__(self, session_id=None, user=None):
        #self.department_code = '1050201'
        #self.clinic_date = '2016-08-05'
        #self.pri_doc_codes = ['3347']
        self.department_code = '1130101'
        self.clinic_date = '2016-08-06'
        self.pri_doc_codes = ['227']

        if user == 'june':
            self.username = '33018319880723262X'
            self.password = '50b9c7460c357fd900fa49b2c50700fe5efae5622025652162e3057eefe8482e'
            self.card_id = 27317
        else:
            self.username = '331004198502121830'
            self.password = 'c714f40f5b9f92a9693dca45932f77cf0365a1e44b36f57eaead0892d6aa7f83'
            self.card_id = 58809

        self.session_id = session_id

        self.api_url = "http://app.hzwsjsw.gov.cn/api/exec.htm"
        self.headers = {'Accept': 'application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5',
            'Content-type': 'application/x-www-form-urlencoded;charset=utf-8',
            'Host': 'app.hzwsjsw.gov.cn',
            'Connection': 'Keep-Alive',
            'User-Agent': 'health'}
        self.cookies = None

    def process(self):
        if not self.session_id:
            # login first
            print("Start login...")
            res_login = self.login_with_hashed_pwd()
            if not res_login:
                print("Failed to login")
                return

            print('Login success.')
            print('session id: ' + self.session_id)

        print("Query available departments...")
        j = self.query_visible_departments()
        if j is None or int(j['ret_code']) != 0:
            print("Error: query available departments.")
            return

        print("Query available doctors...")
        doctors = self.query_visible_doctors()
        if doctors is None or len(doctors) == 0:
            print("Error: no available doctors.")
            return

        succeed = False
        for doctor in doctors:
            print("Query doctor's schedules: ")
            doctor.print_info()
            schedules = self.query_visible_schedules(doctor.doctor_code)
            if schedules is None:
                print("Error: query schedules.")
                return
            elif len(schedules) == 0:
                print("No schedules for the doctor.")
                continue

            # in reversed order.
            for schedule in reversed(schedules):
                appo_result = self.submit_appointment(schedule)
                if not appo_result is None:
                    print("Succeed:")
                    appo_result.print_info()
                    succeed = True
                    break

            if succeed:
                break;

    def post_request(self, data, headers=None, cookies=None, auto_login=True):
        r = requests.post(self.api_url, data=data, headers=self.headers, cookies=cookies)
        if r.status_code == 200:
            res_content = r.content
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
                    new_data, number = re.subn('"session_id":"[a-zA-Z0-9\-_]+"', '"session_id":"%s"' % (self.session_id), data)
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
            return self.reorder_doctors(doctors, self.pri_doc_codes)

        return None

    def reorder_doctors(self, doctors, pri_list):
        if doctors is None or len(doctors) <= 1 or pri_list is None or len(pri_list) == 0:
            return doctors

        # add doctors with priority first
        sorted_doctors = []
        for pri in pri_list:
            f_doctor = self.find_by_doctor_code(doctors, pri)
            if f_doctor:
                sorted_doctors.append(f_doctor)

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
        if j and int(j['ret_code']) == 0:
            return self.parse_json_list(j['list'], Schedule)
        elif j and int(j['ret_code']) == 1:
            # request success but no data.
            return []

        return None

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


def main():
    args = docopt(__doc__)

    #appointment = Appointment(args["USERNAME"], args["PASSWORD"], args["DEPART_CODE"], args["DOCTOR_CODE"])
    appointment = Appointment(session_id='71402ff0528997616e8bb864f397c503cdeca50da9e7b20d0a27d0ad4748c6ca', user='jinde')
    appointment.process();

if __name__ == "__main__":
    main()