wget https://www.python.org/ftp/python/3.6.5/Python-3.6.5.tgz
tar xvf Python-3.6.5.tgz
cd Python-3.6.5
./configure --enable-optimizations
make -j8
sudo make altinstall
