#!/bin/sh

git config --global user.email "travis@travis-ci.org"
git config --global user.name "Travis CI"

git remote add origin-with-token https://${GH_TOKEN}@github.com/MVSE-outreach/resources.git > /dev/null 2>&1

