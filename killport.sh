#!/bin/bash

# get the argument port
port="$1"
echo "Killing service running on port=> $port"
sudo kill -9 $(sudo lsof -t -i:$port)