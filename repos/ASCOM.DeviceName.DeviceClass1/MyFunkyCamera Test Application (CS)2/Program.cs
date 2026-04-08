// This implements a console application that can be used to test an ASCOM driver
//

// This is used to define code in the template that is specific to one class implementation
// unused code can be deleted and this definition removed.

#define Camera
// remove this to bypass the code that uses the chooser to select the driver
#define UseChooser

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace ASCOM
{
    public class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            // Uncomment the code that's required
#if UseChooser
            // choose the device
            string id = ASCOM.DriverAccess.Camera.Choose("");
            if (string.IsNullOrEmpty(id))
                return;
            // create this device
            ASCOM.DriverAccess.Camera device = new ASCOM.DriverAccess.Camera(id);
#else
            // this can be replaced by this code, it avoids the chooser and creates the driver class directly.
            ASCOM.DriverAccess.Camera device = new ASCOM.DriverAccess.Camera("ASCOM.MyFunkyCamera.Camera");
#endif
            // now run some tests, adding code to your driver so that the tests will pass.
            // these first tests are common to all drivers.
            Console.WriteLine("name " + device.Name);
            Console.WriteLine("description " + device.Description);
            Console.WriteLine("DriverInfo " + device.DriverInfo);
            Console.WriteLine("driverVersion " + device.DriverVersion);

            // TODO add more code to test the driver.
            device.Connected = true;
            device.CoolerOn = false;
            short mbx = device.MaxBinX;
           
            device.NumX = 500;
            device.NumY = 500;
            device.BinX = 1;
            device.BinY = 1;
            device.StartExposure(0.5, true);

            Console.WriteLine("Press Enter to read the Image");
            Console.ReadLine();
            int[,] image = (int[,])device.ImageArray;


            /*
            for (int i = 0; i < 1; i++)
            {
                device.StartExposure(50, true);
                Console.WriteLine("Press Enter to get the Image");
                Console.ReadLine();
                int[,] image = (int[,])device.ImageArray;
                Console.WriteLine("cycle number {0}", i);
            }
            */

            device.Connected = false;
 //           Console.WriteLine("Press Enter to finish");
 //           Console.ReadLine();
        }
    }
}

