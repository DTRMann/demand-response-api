#!/bin/bash

echo "Creating event..."
curl -X POST http://localhost:5000/events -H "Content-Type: application/json" -d @test_event_create.json

echo ""
echo ""
echo "Listing all events..."
curl http://localhost:5000/events