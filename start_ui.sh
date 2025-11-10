#!/bin/bash

echo "🎬 Video Take Selector UI"
echo "=========================="
echo ""
echo "Installing Flask if needed..."
pip3 install Flask

echo ""
echo "Starting web server..."
echo "📱 Open your browser to: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 video_selector_ui.py

