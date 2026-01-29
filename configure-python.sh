#!/bin/bash

echo "**************************************************"
echo "Installing Python 3 and pip..."
echo "**************************************************"
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv

echo "**************************************************"
echo "Creating a virtual environment..."
echo "**************************************************"
python3 -m venv venv

echo "**************************************************"
echo "Activating the virtual environment..."
echo "**************************************************"
source venv/bin/activate

echo "**************************************************"
echo "Installing the required packages..."
echo "**************************************************"
venv/bin/pip install -r requirements.txt