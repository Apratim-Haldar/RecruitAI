import React, { useState } from 'react';
import { UserCheck, UserX } from 'lucide-react';

type candidate = {
    id: string;
    name:string;
    email:string;
    experience: number;
    skills:string[];
    education:string[];
    appliedFor: string;
    status:string;
}
export default function CandidateList() {
  const [selectedCandidate, setSelectedCandidate] = useState<candidate | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const candidates = [
    {
      id: '1',
      name: 'Sarah Wilson',
      email: 'sarah.wilson@example.com',
      experience: 5,
      skills: ['React', 'TypeScript', 'Node.js'],
      education: 'Masters in Computer Science',
      appliedFor: 'Senior Frontend Developer',
      status: 'new'
    },
    {
      id: '2',
      name: 'Michael Chen',
      email: 'michael.chen@example.com',
      experience: 7,
      skills: ['Product Management', 'Agile', 'User Research'],
      education: 'MBA',
      appliedFor: 'Product Manager',
      status: 'shortlisted'
    }
  ];

  const openModal = (candidate: candidate) => {
    setSelectedCandidate(candidate);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setSelectedCandidate(null);
    setIsModalOpen(false);
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">Recent Candidates</h2>
      </div>
      <div className="divide-y divide-gray-200">
        {candidates.map(candidate => (
          <div
            key={candidate.id}
            className="p-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <img
                  className="h-10 w-10 rounded-full"
                  src={`https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name)}&background=random`}
                  alt={candidate.name}
                />
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-gray-900">{candidate.name}</h3>
                  <p className="text-sm text-gray-500">{candidate.appliedFor}</p>
                </div>
              </div>
              <div className="flex space-x-2 z-1">
                <button className="p-2 text-green-600 hover:bg-green-100 rounded-full">
                  <UserCheck className="w-5 h-5" />
                </button>
                <button className="p-2 text-red-600 hover:bg-red-100 rounded-full">
                  <UserX className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="mt-4">
              <div className="flex flex-wrap gap-2">
                {candidate.skills.map(skill => (
                  <span
                    key={skill}
                    className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full"
                  >
                    {skill}
                  </span>
                ))}
                <button onClick={() => openModal(candidate)} className="px-2 py-1 hover:bg-pink-600 cursor-pointer text-xs font-semibold bg-pink-500 text-white rounded-full">More Details</button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {isModalOpen && selectedCandidate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 bg-opacity-50">
          <div className="bg-white rounded-lg shadow-lg w-96 p-6">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-semibold text-gray-900">
                {selectedCandidate.name}
              </h3>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <div className="mt-4">
              <p className="text-sm text-gray-500">
                <strong>Email:</strong> {selectedCandidate.email}
              </p>
              <p className="text-sm text-gray-500">
                <strong>Experience:</strong> {selectedCandidate.experience} years
              </p>
              <p className="text-sm text-gray-500">
                <strong>Education:</strong> {selectedCandidate.education}
              </p>
              <p className="text-sm text-gray-500">
                <strong>Applied For:</strong> {selectedCandidate.appliedFor}
              </p>
              <div className="mt-4">
                <h4 className="text-sm font-medium text-gray-900">Skills:</h4>
                <div className="flex flex-wrap gap-2 mt-2">
                  {selectedCandidate.skills.map(skill => (
                    <span
                      key={skill}
                      className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={closeModal}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}