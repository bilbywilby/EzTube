#!/bin/bash

echo "Checking system requirements..."

# Check for Python
if ! command -v python3 &> /dev/null; then
  echo "Python3 is not installed. Please install Python3 to continue."
  exit 1
fi

# Check for pip
if ! command -v pip3 &> /dev/null; then
  echo "pip3 is not installed. Installing pip3..."
  python3 -m ensurepip --upgrade
fi

# Check for FFmpeg
if ! command -v ffmpeg &> /dev/null; then
  echo "FFmpeg is not installed. Please install FFmpeg to use advanced features."
  echo "On Ubuntu/Debian: sudo apt install ffmpeg"
  echo "On MacOS: brew install ffmpeg"
  exit 1
fi

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo "All dependencies installed successfully!"
