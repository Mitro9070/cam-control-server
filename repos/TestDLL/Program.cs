using System;
using System.Runtime.InteropServices;
using System.Text;   // StringBuilder

//namespace TestDLL
//{
class Program {
    /*
    [DllImport("SimplestNativeDLL.dll")]        
    public static extern int fnSampleNativeDLL();
    [DllImport("SimplestNativeDLL.dll")]
    public static extern int SetConnectionType(int type, out int status1, out int status);
*/
    //[DllImport("SimplestNativeDLL.dll")]
    //public static extern int CopyFunc([MarshalAs(UnmanagedType.LPStr)] string a, [MarshalAs(UnmanagedType.LPStr)] string b);
    
    //[DllImport("SimplestNativeDLL.dll")]
    //    public static extern bool ConnectCamera(out int modelId, [Out][MarshalAs(UnmanagedType.LPStr)] out string modelStr, out int statusMSG, int addr);
    
    //[DllImport("SimplestNativeDLL.dll", ExactSpelling = false, CharSet = CharSet.Auto, CallingConvention = CallingConvention.Cdecl, SetLastError = true)]
    [DllImport("SimplestNativeDLL.dll", ExactSpelling = false, CallingConvention = CallingConvention.Cdecl, SetLastError = true)]
    public static extern bool ConnectCamera(out int modelId, out IntPtr ptrToModelStr, out int statusMSG, int addr);
//    public static extern bool ConnectCamera(out int modelId, out StringBuilder modelStr, out int statusMSG, int addr);


    [DllImport("SimplestNativeDLL.dll", CallingConvention = CallingConvention.Cdecl, SetLastError = true)]
    public static extern bool GetMeasuredData(ushort[] pInDataStart, out int writeBytes, out int readBytes, out int statusMSG, int addr);
    private static readonly uint nRows = 50;
    private static readonly uint nCols = 100;
    private static ushort[] pInDataStart;
    private static int[,] image;

    private static bool initArrays()
    {
        pInDataStart = new ushort[nRows * nCols];
        image = new int[nRows, nCols];
        return true;
    }

    private static bool getSafeArray()
    {
        int index = 0;
        for (int i = 0; i < nRows; i++)
        {
            for (int j = 0; j < nCols; j++)
            {
                image[i, j] = pInDataStart[index];
                index++;
            }
        }
        return true;
    }
    static void Main()
    {
        initArrays();
        Console.WriteLine("Hello World!");
        //Console.WriteLine(111);
        //Console.WriteLine(fnSampleNativeDLL());
        //      string ipStr = "This is my funky ip address";
        //int copylen = ipStr.Length;

        //       IntPtr ipPtr = Marshal.StringToHGlobalAnsi(ipStr);
        //string k = "kkk";
        //int stat;
        //int stat1;
        //int res = SetConnectionType(12, out stat1, out stat);
        //Console.WriteLine(stat);
        //Console.WriteLine(stat1);
        //Console.WriteLine(res);
        //string a = "aaaa";
        //string b = "bbb";
        //int res1 = CopyFunc(a, b);
        //Console.WriteLine(a);
        //Console.WriteLine(b);
        //Console.WriteLine(res1);

        int modelId;
        // string modelStr;
        int statusMSG;
        int addr = 0;
        int writeBytes, readBytes;
        bool res;

        //string modelStr;
        //StringBuilder modelStr = new StringBuilder(100);
        IntPtr ptrToModelStr = new IntPtr(0);
//        res = ConnectCamera(out modelId, out modelStr, out statusMSG, addr);
        res = ConnectCamera(out modelId, out ptrToModelStr, out statusMSG, addr);
        string modelStr = Marshal.PtrToStringAnsi(ptrToModelStr);
        Console.WriteLine("res = {0} modelId = {1} modelStr = {2}", res, modelId, modelStr);

        res = GetMeasuredData(pInDataStart, out writeBytes, out readBytes, out statusMSG, addr);
        Console.WriteLine("res = {0} writebytes = {1} readBytes = {2}", res, writeBytes, readBytes);

        //IntPtr pInDataStart;
        //System.UInt16 sizeOfData;
        //sizeOfData = 6;
        //int len = 6;

        //bool resbool = GetMeasuredData(pInDataStart, out writebytes);
        getSafeArray();
        Console.WriteLine(pInDataStart[5]);
        /*
        foreach (int item in image)
        {
            Console.WriteLine(item + " ");
        }
        */
        Console.WriteLine(image);
        Console.WriteLine("Press Enter to finish");
        Console.ReadLine();
    }
}
//}
