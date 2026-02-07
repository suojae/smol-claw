#!/bin/bash
# Test script for autonomous AI server

echo "🧪 Testing Autonomous AI Server"
echo ""

# Status check
echo "1️⃣ Status check:"
curl http://localhost:3000/status
echo -e "\n"

# Manual think trigger
echo "2️⃣ Manual think trigger:"
curl http://localhost:3000/think
echo -e "\n"

echo "✅ Tests complete!"
