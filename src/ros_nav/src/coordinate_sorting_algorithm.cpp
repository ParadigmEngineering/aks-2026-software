//This cpp script seperates the data in the track coordinates into two files; one containing the latitudes, the other containing the longitudes.
#include <fstream>
#include <string>

using namespace std;

string coordinate; //This string variable will store the coordinate read from the file.


ifstream read("trackcoordinates.txt");
ofstream writelongitude("longitudes.txt", ios::app);
ofstream writelatitude("latitudes.txt", ios::app);

int main()
{
	while(read>>coordinate)
	{
		if(coordinate[0] == '-')
		{writelongitude<<coordinate<<endl;}
		
		else if(coordinate[0] == '4')
		{if(coordinate.back()==','){coordinate.pop_back();}
			writelatitude<<coordinate<<endl;}
	}
	read.close();
	writelatitude.close();
	writelongitude.close();
	return 0;
}

