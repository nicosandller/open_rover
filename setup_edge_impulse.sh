sudo apt update
sudo apt upgrade

# wget https://unofficial-builds.nodejs.org/download/release/v12.13.0/node-v12.13.0-linux-armv6l.tar.xz
# tar xvf node-v12.13.0-linux-armv6l.tar.xz
# cd node-v12.13.0-linux-armv6l
# sudo cp -R bin/* /usr/bin/
# sudo cp -R lib/* /usr/lib/


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