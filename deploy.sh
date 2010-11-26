#!/bin/bash
echo 
echo "##############################"
echo "Deploying new version of branch" 
git branch | grep "*"
echo "##############################"
echo 


clean=$(git status | grep -c "working directory clean")
[ "$clean" == "1" ] || {
  echo "Commit your changes first"
  exit
}

appcfg.py update . -e robcos@robcos.com
