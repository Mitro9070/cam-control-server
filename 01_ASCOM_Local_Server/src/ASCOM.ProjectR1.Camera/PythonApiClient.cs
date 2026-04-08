using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;
using System.Web.Script.Serialization;

namespace ASCOM.ProjectR1
{
    internal sealed class PythonApiClient
    {
        internal sealed class BinaryApiResponse
        {
            public byte[] Data { get; set; } = Array.Empty<byte>();
            public Dictionary<string, string> Headers { get; set; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        }

        private readonly string _baseUrl;
        private readonly JavaScriptSerializer _serializer = new JavaScriptSerializer();

        public PythonApiClient(string baseUrl = null)
        {
            var envUrl = Environment.GetEnvironmentVariable("PROJECT_R1_API_BASE_URL");
            var resolved = string.IsNullOrWhiteSpace(baseUrl)
                ? (string.IsNullOrWhiteSpace(envUrl) ? "http://127.0.0.1:3037/api/v1" : envUrl)
                : baseUrl;
            _baseUrl = resolved.TrimEnd('/');
        }

        public Dictionary<string, object> GetJson(string path)
        {
            var request = CreateRequest("GET", path, null);
            return Send(request);
        }

        public Dictionary<string, object> PostJson(string path, object body = null)
        {
            var json = body == null ? "{}" : _serializer.Serialize(body);
            var request = CreateRequest("POST", path, json);
            return Send(request);
        }

        public Dictionary<string, object> PutJson(string path, object body)
        {
            var json = _serializer.Serialize(body);
            var request = CreateRequest("PUT", path, json);
            return Send(request);
        }

        public BinaryApiResponse GetBinary(string path)
        {
            var request = CreateRequest("GET", path, null);
            using (var response = (HttpWebResponse)request.GetResponse())
            using (var stream = response.GetResponseStream() ?? Stream.Null)
            using (var ms = new MemoryStream())
            {
                stream.CopyTo(ms);
                var headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                foreach (var key in response.Headers.AllKeys)
                {
                    if (!string.IsNullOrWhiteSpace(key))
                    {
                        headers[key] = response.Headers[key];
                    }
                }

                return new BinaryApiResponse
                {
                    Data = ms.ToArray(),
                    Headers = headers
                };
            }
        }

        private HttpWebRequest CreateRequest(string method, string path, string jsonBody)
        {
            var req = (HttpWebRequest)WebRequest.Create($"{_baseUrl}{path}");
            req.Method = method;
            req.ContentType = "application/json";
            req.Accept = "application/json";
            req.Timeout = 30000;
            req.ReadWriteTimeout = 30000;

            if (!string.IsNullOrEmpty(jsonBody))
            {
                using (var stream = new StreamWriter(req.GetRequestStream(), Encoding.UTF8))
                {
                    stream.Write(jsonBody);
                }
            }

            return req;
        }

        private Dictionary<string, object> Send(HttpWebRequest request)
        {
            using (var response = (HttpWebResponse)request.GetResponse())
            using (var reader = new StreamReader(response.GetResponseStream() ?? Stream.Null))
            {
                var json = reader.ReadToEnd();
                if (string.IsNullOrWhiteSpace(json))
                {
                    return new Dictionary<string, object>();
                }
                return _serializer.Deserialize<Dictionary<string, object>>(json);
            }
        }
    }
}
