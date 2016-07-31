#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase
import json
from appointment import Appointment
from appointment import Doctor
from appointment import Schedule

class TestAppointment(TestCase):
    def setUp(self):
        self.app = Appointment()
        self.j_doc_list = json.loads('[{"dept_code":"1050201","dept_name":"产科门诊","doctor_code":"3347","doctor_name":"翟洪波","doctor_position":"主任医师","clinic_date":"2016-08-05","clinic_type":"4"}]')
        self.doctors = [Doctor(u'翟洪波', u'3347', u'2016-08-05')]

    def tearDown(self):
        pass

    def test_process(self):
        #self.fail()
        pass

    def test_post_request(self):
        #self.fail()
        pass

    def test_login_with_hashed_pwd(self):
        #self.fail()
        pass

    def test_query_visible_departments(self):
        #self.fail()
        pass

    def test_query_visible_doctors(self):
        #self.fail()
        pass

    def test_parse_json_list(self):
        parsed_doctors = self.app.parse_json_list(self.j_doc_list, Doctor)
        self.assertSequenceEqual(self.doctors, parsed_doctors, 'error pass visible doctors')
        pass

    def test_reorder_doctors(self):
        doctors = [Doctor(u'翟洪波', u'3347', u'2016-08-05'), Doctor(u'翟洪波2', u'3348', u'2016-08-05'), Doctor(u'翟洪波3', u'3349', u'2016-08-05')]
        pri_list = [u'3348', u'111111']
        sorted_doctors = [Doctor(u'翟洪波2', u'3348', u'2016-08-05'), Doctor(u'翟洪波', u'3347', u'2016-08-05'), Doctor(u'翟洪波3', u'3349', u'2016-08-05')]
        pri_list2 = [u'3349', u'123456', u'3348']
        sorted_doctors2 = [Doctor(u'翟洪波3', u'3349', u'2016-08-05'), Doctor(u'翟洪波2', u'3348', u'2016-08-05'), Doctor(u'翟洪波', u'3347', u'2016-08-05')]

        ret_doctors = self.app.reorder_doctors(doctors, pri_list)
        ret_doctors2 = self.app.reorder_doctors(doctors, pri_list2)

        self.assertSequenceEqual(sorted_doctors, ret_doctors, 'error reorder doctors')
        self.assertSequenceEqual(sorted_doctors2, ret_doctors2, 'error reorder doctors')

    def test_query_visible_appointments(self):
        #self.fail()
        pass

    def test_submit_appointments(self):
        #self.fail()
        pass

    def test_try_submit_appointment(self):
        #self.fail()
        pass
