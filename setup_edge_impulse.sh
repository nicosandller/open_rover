sudo apt update
sudo apt upgrade


#increase swap file memory
free -h
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h


# install NVM (node version management)
sudo apt update
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm —version
# install node
nvm install --lts
source ~/.bashrc
node --version
# install npm
npm install -g npm@10.4.0
source ~/.bashrc

# https://forum.edgeimpulse.com/t/install-on-raspberry-pi-zero-solved/3722
sudo apt install -y gcc g++ make build-essential sox gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-base gstreamer1.0-plugins-base-apps

sudo npm install edge-impulse-linux -g --unsafe-perm

# change permisions on file
sudo chmod +x /usr/local/bin/edge-impulse-linux
sudo chmod +x /usr/local/bin/edge-impulse-linux-runner