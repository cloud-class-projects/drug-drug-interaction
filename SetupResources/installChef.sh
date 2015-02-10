curl -L https://www.opscode.com/chef/install.sh | bash
wget http://github.com/opscode/chef-repo/tarball/master
tar -zxf master
mv opscode-chef-repo* chef-repo
rm master
cd chef-repo/
mkdir .chef
echo "cookbook_path ['/home/ubuntu/chef-repo/cookbooks']" > .chef/knife.rb
cd cookbooks
knife cookbook site download java
knife cookbook site download apt
knife cookbook site download yum
knife cookbook site download hadoop
tar -zxf java*
tar -zxf apt*
tar -zxf yum*
tar -zxf hadoop*
rm *.tar.gz
