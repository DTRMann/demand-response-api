import unittest
import json
from datetime import datetime, timedelta
from flask import Flask
from app import app, events_db, DemandResponseEvent, EventLevel

class DemandResponseApiTest(unittest.TestCase):
    def setUp(self):
        # Create a test client
        self.app = app
        self.client = self.app.test_client()
        self.client.testing = True
        
        # Clear the events database before each test
        events_db.clear()
        
        # Create some sample event data
        self.sample_event = {
            "level": "High",
            "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.now() + timedelta(hours=3)).isoformat(),
            "requesting_entity": "Test Utility",
            "message": "Please reduce consumption",
            "metadata": {"region": "North", "priority": 1}
        }
        
        # Add a test event that's currently active
        active_event = DemandResponseEvent(
            level=EventLevel.CRITICAL,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now() + timedelta(hours=1),
            requesting_entity="Active Utility",
            message="Ongoing event"
        )
        events_db.append(active_event)

    def test_create_event_POST(self):
        
        """Test creating a new event with POST request"""
        response = self.client.post(
            '/events/',
            data=json.dumps(self.sample_event),
            content_type='application/json'
        )
        
        # Check response status code is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check the event has been added to database
        self.assertEqual(len(events_db), 2)  # 1 from setup + 1 new
        
        # Check response data contains event info
        data = json.loads(response.data)
        self.assertEqual(data['requesting_entity'], 'Test Utility')
        self.assertEqual(data['level'], 'High')
        
        # Verify the event has a generated UUID
        self.assertTrue('id' in data)
        self.assertIsNotNone(data['id'])

    def test_get_active_events(self):
        
        """Test retrieving active events"""
        response = self.client.get('/events/active')
        
        # Check status code
        self.assertEqual(response.status_code, 200)
        
        # Check that active events exists
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['requesting_entity'], 'Active Utility')
        self.assertEqual(data[0]['level'], 'Critical')

    def test_filter_events_by_entity(self):
        
        """Test filtering events by requesting entity"""
        # Add another event for a different entity
        other_event = DemandResponseEvent(
            level=EventLevel.HIGH,
            start_time=datetime.now() + timedelta(hours=2),
            end_time=datetime.now() + timedelta(hours=4),
            requesting_entity="Other Utility"
        )
        events_db.append(other_event)
        
        # Get only events for a specific entity
        response = self.client.get('/events/?entity=Active Utility')
        
        # Check we got exactly one result
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['requesting_entity'], 'Active Utility')


    def test_database_persistence(self):
        
        """Test that events are properly stored in the database"""
        # Add a new event
        new_event = DemandResponseEvent(
            level=EventLevel.HIGH,
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=2),
            requesting_entity="Database Test Entity",
            message="Testing database persistence"
        )
        events_db.append(new_event)
        
        # Get future events which should include our new event
        response = self.client.get('/events/future')
        
        # Check the new event is in the response
        data = json.loads(response.data)
        found = False
        for event in data:
            if event['requesting_entity'] == "Database Test Entity":
                found = True
                self.assertEqual(event['message'], "Testing database persistence")
        
        self.assertTrue(found, "Event was not found in database")
        
        # Verify event count
        self.assertTrue(len(events_db) >= 2)  # At least the active event and our new one

if __name__ == '__main__':
    unittest.main()

