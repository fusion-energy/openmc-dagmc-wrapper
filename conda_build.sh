
#assumes anaconda-client and conda-build have been installed
# conda install -y anaconda-client
# conda install -y conda-build
# anaconda login


rm -rf /tmp/conda-build
mkdir -p /tmp/conda-build
rm -rf /tmp/conda-build


# VERSION=$(echo $GITHUB_REF | sed 's#.*/v##')
VERSION=0.0.9
PLACEHOLDER='version="develop"'
VERSION_FILE='setup.py'
# Grep checks that the placeholder is in the file. If grep doesn't find
# the placeholder then it exits with exit code 1 and github actions fails.
grep "$PLACEHOLDER" "$VERSION_FILE"
sed -i "s/$PLACEHOLDER/version=\"${VERSION}\"/g" "$VERSION_FILE"

conda-build conda/ -c fusion-energy -c cadquery -c conda-forge --croot /tmp/conda-build 

# converting using all includes quite a few oxs and linux versions (arm arch etc)
# conda convert /tmp/conda-build/linux-64/*.tar.bz2 --platform all  -o /tmp/conda-build

# option for converting package to specified platforms
# platforms=( osx-64 linux-32 linux-64 win-32 win-64 )
# find /tmp/conda-build/linux-64/ -name *.tar.bz2 | while read file
# do
#     echo $file
#     for platform in "${platforms[@]}"
#     do
#        conda convert --platform $platform $file  -o /tmp/conda-build/
#     done
# done

# anaconda upload -f /tmp/conda-build/*/*.tar.bz2

sed -i "s/version=\"${VERSION}\"/$PLACEHOLDER/g" "$VERSION_FILE"
