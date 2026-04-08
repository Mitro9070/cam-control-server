using System;
using System.Collections.Generic;
using System.Globalization;

namespace ASCOM.ProjectR1
{
    public static class CameraApiValueReader
    {
        public static bool ReadBool(Dictionary<string, object> data, string key)
        {
            return Convert.ToBoolean(ReadRequired(data, key), CultureInfo.InvariantCulture);
        }

        public static int ReadInt(Dictionary<string, object> data, string key)
        {
            return Convert.ToInt32(ReadRequired(data, key), CultureInfo.InvariantCulture);
        }

        public static double ReadDouble(Dictionary<string, object> data, string key)
        {
            return Convert.ToDouble(ReadRequired(data, key), CultureInfo.InvariantCulture);
        }

        public static string ReadString(Dictionary<string, object> data, string key)
        {
            var value = ReadRequired(data, key);
            return Convert.ToString(value, CultureInfo.InvariantCulture) ?? string.Empty;
        }

        public static bool TryReadString(Dictionary<string, object> data, string key, out string value)
        {
            value = string.Empty;
            if (data == null || string.IsNullOrWhiteSpace(key)) return false;
            if (!data.TryGetValue(key, out var raw) || raw == null) return false;
            value = Convert.ToString(raw, CultureInfo.InvariantCulture) ?? string.Empty;
            return true;
        }

        public static bool TryReadInt(Dictionary<string, object> data, string key, out int value)
        {
            value = 0;
            if (data == null || string.IsNullOrWhiteSpace(key)) return false;
            if (!data.TryGetValue(key, out var raw) || raw == null) return false;
            value = Convert.ToInt32(raw, CultureInfo.InvariantCulture);
            return true;
        }

        private static object ReadRequired(Dictionary<string, object> data, string key)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));
            if (string.IsNullOrWhiteSpace(key)) throw new ArgumentException("key must not be empty", nameof(key));
            if (!data.TryGetValue(key, out var value))
            {
                throw new KeyNotFoundException($"Response key not found: {key}");
            }
            return value;
        }
    }
}
