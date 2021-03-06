#!/usr/bin/env python

"""
@file ion/services/sa/instrument/test/test_instrument_management_service.py
@author Ian Katz
@test ion.services.sa.instrument.instrument_management_service Unit test suite to cover all service code
"""


#from mock import Mock #, sentinel, patch
from ion.services.sa.instrument.instrument_management_service import InstrumentManagementService
from nose.plugins.attrib import attr



from ooi.logging import log

from ion.services.sa.resource_impl.resource_impl_metatest import ResourceImplMetatest

from ion.services.sa.instrument.instrument_agent_instance_impl import InstrumentAgentInstanceImpl
from ion.services.sa.instrument.instrument_agent_impl import InstrumentAgentImpl
from ion.services.sa.instrument.instrument_device_impl import InstrumentDeviceImpl
from ion.services.sa.instrument.instrument_model_impl import InstrumentModelImpl
from ion.services.sa.instrument.platform_agent_instance_impl import PlatformAgentInstanceImpl
from ion.services.sa.instrument.platform_agent_impl import PlatformAgentImpl
from ion.services.sa.instrument.platform_device_impl import PlatformDeviceImpl
from ion.services.sa.instrument.platform_model_impl import PlatformModelImpl
from ion.services.sa.instrument.sensor_device_impl import SensorDeviceImpl
from ion.services.sa.instrument.sensor_model_impl import SensorModelImpl

#from pyon.core.exception import BadRequest, Conflict, Inconsistent, NotFound
import unittest
from pyon.util.unit_test import PyonTestCase


@attr('UNIT', group='sa')
class TestInstrumentManagement(PyonTestCase):

    def setUp(self):
        self.mock_ionobj = self._create_IonObject_mock('ion.services.sa.instrument.instrument_management_service.IonObject')

        #self.mock_ionobj = IonObject
        mock_clients = self._create_service_mock('instrument_management')

        self.instrument_mgmt_service = InstrumentManagementService()
        self.instrument_mgmt_service.clients = mock_clients
        
        # must call this manually
        self.instrument_mgmt_service.on_init()

        self.addCleanup(delattr, self, "instrument_mgmt_service")
        self.addCleanup(delattr, self, "mock_ionobj")
        #self.resource_impl_cleanup()

    #def resource_impl_cleanup(self):
        #pass

rim = ResourceImplMetatest(TestInstrumentManagement, InstrumentManagementService, log)
rim.test_all_in_one(True)

rim.add_resource_impl_unittests(InstrumentAgentImpl, {"driver_module": "potato"})
rim.add_resource_impl_unittests(InstrumentDeviceImpl, {"serial_number": "123", "firmware_version": "x"})
rim.add_resource_impl_unittests(PlatformAgentImpl, {"description": "the big donut"})
rim.add_resource_impl_unittests(PlatformDeviceImpl, {"serial_number": "2345"})
rim.add_resource_impl_unittests(PlatformModelImpl, {"description": "desc"})
rim.add_resource_impl_unittests(SensorDeviceImpl, {"serial_number": "123"})


